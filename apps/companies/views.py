"""Views publicas do app companies."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.db import IntegrityError
from django.shortcuts import redirect
from django.views.generic.edit import FormView

from apps.companies.forms import SaasTenantRegistrationForm
from apps.companies.services.saas_registration import register_company_and_primary_admin
from apps.companies.services.tenant_scope import TenantScopeService


class SaasTenantRegistrationView(FormView):
    template_name = "accounts/saas_signup.html"
    form_class = SaasTenantRegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL or "/ecossistema/")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            user, company = register_company_and_primary_admin(form=form)
        except IntegrityError:
            form.add_error("admin_email", "Nao foi possivel concluir o cadastro. Verifique os dados ou tente novamente.")
            return self.form_invalid(form)
        auth_login(self.request, user)
        TenantScopeService.set_active_context(self.request, company_id=company.id)
        messages.success(
            self.request,
            "Cadastro realizado com sucesso. Bem-vindo ao SMART360.",
        )
        return redirect(settings.LOGIN_REDIRECT_URL)
