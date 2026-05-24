"""CRUD minimos de tenants (Company) no Admin Shell — /app/dashboard/companies/."""

from __future__ import annotations

from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from apps.admin_shell.views import ShellContextMixin

from apps.companies.forms import CompanyShellForm
from apps.companies.models import Company
from apps.companies.services.company_shell_access import (
    attach_primary_membership,
    scoped_companies_for_user,
    user_can_create_saas_company,
    user_can_manage_company_record,
    user_can_open_company_shell,
)


class CompanyShellBase(ShellContextMixin):
    permission_domain = None
    enforce_billing_access = False
    permission_action = "view"
    resource_type = "saas_company_shell"

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            return self.handle_no_permission()
        if not user_can_open_company_shell(request.user):
            return HttpResponseForbidden("Acesso negado.")
        return super().dispatch(request, *args, **kwargs)


class CompanyShellListView(CompanyShellBase, TemplateView):
    template_name = "admin_shell/companies/company_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        companies = scoped_companies_for_user(self.request.user)
        ctx["companies"] = companies
        ctx["can_create_company"] = user_can_create_saas_company(self.request.user)
        ctx["page_title"] = "Empresas SaaS"
        ctx["page_description"] = "Tenants assinantes da plataforma e isolamento de dados."
        ctx["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Empresas", "url": None},
        ]
        ctx["current_module_slug"] = "billing"
        return ctx


class CompanyShellDetailView(CompanyShellBase, TemplateView):
    template_name = "admin_shell/companies/company_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = get_object_or_404(scoped_companies_for_user(self.request.user), pk=self.kwargs["company_id"])
        ctx["company"] = company
        ctx["can_edit"] = user_can_manage_company_record(self.request.user, company)
        ctx["can_toggle_status"] = user_can_create_saas_company(self.request.user)
        ctx["page_title"] = company.name
        ctx["page_description"] = company.legal_name or company.slug
        ctx["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Empresas", "href": reverse("admin-shell:dashboard-companies")},
            {"label": company.name, "url": None},
        ]
        ctx["current_module_slug"] = "billing"
        return ctx


class CompanyShellCreateView(CompanyShellBase, FormView):
    template_name = "admin_shell/companies/company_form.html"
    form_class = CompanyShellForm

    def dispatch(self, request, *args, **kwargs):
        if not user_can_create_saas_company(request.user):
            return HttpResponseForbidden(
                "Apenas perfis de plataforma com permissão de Billing (gerir) ou superusuario podem criar empresas."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["show_membership_checkbox"] = True
        kwargs["allow_status_edit"] = True
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Nova empresa"
        ctx["page_description"] = "Cadastre uma empresa assinante (tenant) do SMART360."
        ctx["form_mode"] = "create"
        ctx["cancel_href"] = reverse("admin-shell:dashboard-companies")
        ctx["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Empresas", "href": reverse("admin-shell:dashboard-companies")},
            {"label": "Nova", "url": None},
        ]
        ctx["current_module_slug"] = "billing"
        return ctx

    def form_valid(self, form):
        company = form.save()
        if form.cleaned_data.get("vincular_usuario_atual"):
            attach_primary_membership(self.request.user, company)
            messages.success(
                self.request,
                "Empresa criada e seu usuario foi vinculado como membro principal.",
            )
        else:
            messages.success(self.request, "Empresa criada com sucesso.")
        return redirect("admin-shell:dashboard-company-detail", company_id=company.pk)


class CompanyShellUpdateView(CompanyShellBase, FormView):
    template_name = "admin_shell/companies/company_form.html"
    form_class = CompanyShellForm

    def dispatch(self, request, *args, **kwargs):
        self.company = scoped_companies_for_user(request.user).filter(pk=self.kwargs["company_id"]).first()
        if self.company is None:
            raise Http404("Empresa não encontrada.")
        if not user_can_manage_company_record(request.user, self.company):
            return HttpResponseForbidden("Sem permissão para alterar esta empresa.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.company
        kwargs["show_membership_checkbox"] = False
        kwargs["allow_status_edit"] = user_can_create_saas_company(self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["company"] = self.company
        ctx["page_title"] = "Editar empresa"
        ctx["page_description"] = self.company.name
        ctx["form_mode"] = "update"
        ctx["cancel_href"] = reverse(
            "admin-shell:dashboard-company-detail",
            kwargs={"company_id": self.company.pk},
        )
        ctx["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Empresas", "href": reverse("admin-shell:dashboard-companies")},
            {
                "label": self.company.name,
                "href": reverse(
                    "admin-shell:dashboard-company-detail",
                    kwargs={"company_id": self.company.pk},
                ),
            },
            {"label": "Editar", "url": None},
        ]
        ctx["current_module_slug"] = "billing"
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Empresa atualizada.")
        return redirect("admin-shell:dashboard-company-detail", company_id=self.company.pk)


class CompanyShellDeactivateView(CompanyShellBase, TemplateView):
    """Alterna empresa entre ativa e inativa — restrito à plataforma."""

    template_name = "admin_shell/companies/company_toggle_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        self.company = scoped_companies_for_user(request.user).filter(pk=self.kwargs["company_id"]).first()
        if self.company is None:
            raise Http404("Empresa não encontrada.")
        if not user_can_create_saas_company(request.user):
            return HttpResponseForbidden(
                "Apenas usuarios autorizados da plataforma podem alterar o status da empresa SaaS."
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.company.status == Company.Status.SUSPENDED:
            messages.error(
                request,
                "Empresas suspensas devem ter o status tratado pela equipe financeira antes de usar este atalho.",
            )
            return redirect("admin-shell:dashboard-company-detail", company_id=self.company.pk)
        if self.company.status == Company.Status.ACTIVE:
            self.company.status = Company.Status.INACTIVE
            msg = "Empresa marcada como inativa."
        else:
            self.company.status = Company.Status.ACTIVE
            msg = "Empresa marcada como ativa."
        self.company.save(update_fields=("status", "updated_at"))
        messages.success(request, msg)
        return redirect("admin-shell:dashboard-company-detail", company_id=self.company.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["company"] = self.company
        ctx["page_title"] = "Alterar status da empresa"
        ctx["will_activate"] = self.company.status != Company.Status.ACTIVE
        ctx["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Empresas", "href": reverse("admin-shell:dashboard-companies")},
            {"label": self.company.name, "url": None},
        ]
        ctx["current_module_slug"] = "billing"
        return ctx
