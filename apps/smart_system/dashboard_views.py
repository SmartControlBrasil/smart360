"""Views do Admin Shell para Plano Rotativo de Inspecao (Smart System).

As rotas sao declaradas em `apps/admin_shell/urls.py`.
"""

from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from apps.admin_shell.security import SmartSystemOperationalRouteMixin
from apps.admin_shell.views import ShellContextMixin

from apps.smart_system.forms import (
    InspectionDivisionEquipmentForm,
    InspectionDivisionForm,
    PreventiveInspectionRoutineForm,
)
from apps.smart_system.models import InspectionDivision, InspectionDivisionEquipment, PreventiveInspectionRoutine
from apps.smart_system.services.inspection_routine_service import get_next_eligible_inspection_division
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def preventive_inspection_routine_url_code(obj: PreventiveInspectionRoutine) -> str:
    return obj.public_id.hex[:12].upper()


def scoped_preventive_routines(request):
    qs = PreventiveInspectionRoutine.objects.select_related("company", "operational_site", "checklist", "next_division")
    return SmartSystemScopeService.scope_queryset(qs, request).order_by("name")


def lookup_preventive_routine(request, code: str) -> PreventiveInspectionRoutine | None:
    slug = code.strip().upper()
    for r in scoped_preventive_routines(request):
        if preventive_inspection_routine_url_code(r) == slug:
            return r
    return None


class SmartInspectionRoutineBase(SmartSystemOperationalRouteMixin, ShellContextMixin):
    permission_domain = "preventive_plans"
    permission_action = "view"

    def breadcrumbs_base(self):
        return [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {
                "label": "Smart System",
                "url": "admin-shell:module-page",
                "route_kwargs": {"module_slug": "smart-system"},
            },
        ]


class SmartSystemInspectionRoutineListView(SmartInspectionRoutineBase, TemplateView):
    template_name = "admin_shell/smart_system/smart_system_inspection_routines_list.html"
    permission_action = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        routines = list(scoped_preventive_routines(self.request))
        next_labels = []
        for r in routines:
            nxt = get_next_eligible_inspection_division(r)
            next_labels.append((r, preventive_inspection_routine_url_code(r), getattr(nxt, "name", "—")))
        context["routine_rows"] = next_labels
        context["page_title"] = "Planos rotativos de inspecao"
        context["page_description"] = "Divisoes configuraveis por unidade/checklist com vinculos a equipamentos (Fase 1)."
        context["breadcrumbs"] = self.breadcrumbs_base() + [{"label": "Planos rotativos", "url": None}]
        context["current_module_slug"] = "smart-system"
        context["page_actions"] = [
            {"label": "Nova rotina", "route_name": "admin-shell:smart-system-inspection-routine-create"},
            {"label": "Planos preventivos", "route_name": "admin-shell:smart-system-preventives"},
        ]
        return context


class SmartSystemInspectionRoutineCreateView(SmartInspectionRoutineBase, FormView):
    template_name = "admin_shell/smart_system/smart_system_inspection_routine_form.html"
    form_class = PreventiveInspectionRoutineForm
    permission_action = "create"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nova rotina de inspecao"
        context["page_description"] = "Unidade operacional + checklist + nome da rotina."
        context["form_mode"] = "create"
        context["breadcrumbs"] = self.breadcrumbs_base() + [
            {"label": "Planos rotativos", "url": "admin-shell:smart-system-inspection-routines"},
            {"label": "Nova", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["routine_code"] = None
        context["cancel_url"] = reverse("admin-shell:smart-system-inspection-routines")
        return context

    def form_valid(self, form):
        instance = form.save()
        messages.success(self.request, "Rotina criada.")
        code = preventive_inspection_routine_url_code(instance)
        return redirect(
            "admin-shell:smart-system-inspection-routine-detail",
            routine_code=code,
        )


class SmartSystemInspectionRoutineUpdateView(SmartInspectionRoutineBase, FormView):
    template_name = "admin_shell/smart_system/smart_system_inspection_routine_form.html"
    form_class = PreventiveInspectionRoutineForm
    permission_action = "update"
    routine: PreventiveInspectionRoutine | None = None

    def dispatch(self, request, *args, **kwargs):
        self.routine = lookup_preventive_routine(request, kwargs["routine_code"])
        if self.routine is None:
            raise Http404("Rotina nao encontrada.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["instance"] = self.routine
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = preventive_inspection_routine_url_code(self.routine)
        context["page_title"] = "Editar rotina"
        context["page_description"] = self.routine.name
        context["form_mode"] = "update"
        context["breadcrumbs"] = self.breadcrumbs_base() + [
            {"label": "Planos rotativos", "url": "admin-shell:smart-system-inspection-routines"},
            {
                "label": code,
                "url": "admin-shell:smart-system-inspection-routine-detail",
                "route_kwargs": {"routine_code": code},
            },
            {"label": "Editar", "url": None},
        ]
        context["current_module_slug"] = "smart-system"
        context["routine_code"] = code
        context["cancel_url"] = reverse(
            "admin-shell:smart-system-inspection-routine-detail",
            kwargs={"routine_code": code},
        )
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Rotina atualizada.")
        code = preventive_inspection_routine_url_code(self.routine)
        return redirect(
            "admin-shell:smart-system-inspection-routine-detail",
            routine_code=code,
        )


class SmartSystemInspectionRoutineDetailView(SmartInspectionRoutineBase, TemplateView):
    template_name = "admin_shell/smart_system/smart_system_inspection_routine_detail.html"
    permission_action = "view"
    routine: PreventiveInspectionRoutine | None = None

    def dispatch(self, request, *args, **kwargs):
        self.routine = lookup_preventive_routine(request, kwargs["routine_code"])
        if self.routine is None:
            raise Http404("Rotina nao encontrada.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = preventive_inspection_routine_url_code(self.routine)
        divisions = (
            InspectionDivision.objects.filter(routine=self.routine)
            .prefetch_related("division_equipment_links__asset")
            .order_by("sort_order", "id")
        )
        next_div = get_next_eligible_inspection_division(self.routine)

        context.update(
            {
                "routine": self.routine,
                "routine_code": code,
                "divisions": divisions,
                "next_eligible": next_div,
                "page_title": self.routine.name,
                "page_description": (
                    "Divisoes e proxima sugerida. Geracao de OS permanece manual nesta fase."
                ),
                "breadcrumbs": self.breadcrumbs_base()
                + [
                    {
                        "label": "Planos rotativos",
                        "url": "admin-shell:smart-system-inspection-routines",
                    },
                    {"label": code, "url": None},
                ],
                "current_module_slug": "smart-system",
            }
        )

        context["page_actions"] = [
            {
                "label": "Editar rotina",
                "route_name": "admin-shell:smart-system-inspection-routine-update",
                "route_kwargs": {"routine_code": code},
                "permission_domain": "preventive_plans",
                "permission_action": "update",
            },
            {
                "label": "Nova divisao",
                "route_name": "admin-shell:smart-system-inspection-division-create",
                "route_kwargs": {"routine_code": code},
                "permission_domain": "preventive_plans",
                "permission_action": "create",
            },
        ]
        return context


class SmartSystemInspectionDivisionCreateView(SmartInspectionRoutineBase, FormView):
    template_name = "admin_shell/smart_system/smart_system_inspection_division_form.html"
    form_class = InspectionDivisionForm
    permission_action = "create"
    routine: PreventiveInspectionRoutine | None = None

    def dispatch(self, request, *args, **kwargs):
        self.routine = lookup_preventive_routine(request, kwargs["routine_code"])
        if self.routine is None:
            raise Http404("Rotina nao encontrada.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = preventive_inspection_routine_url_code(self.routine)
        context.update(
            {
                "routine": self.routine,
                "routine_code": code,
                "division": None,
                "page_title": "Nova divisao",
                "page_description": self.routine.name,
                "breadcrumbs": self.breadcrumbs_base()
                + [
                    {"label": "Planos rotativos", "url": "admin-shell:smart-system-inspection-routines"},
                    {
                        "label": code,
                        "url": "admin-shell:smart-system-inspection-routine-detail",
                        "route_kwargs": {"routine_code": code},
                    },
                    {"label": "Nova divisao", "url": None},
                ],
                "current_module_slug": "smart-system",
                "cancel_url": reverse(
                    "admin-shell:smart-system-inspection-routine-detail",
                    kwargs={"routine_code": code},
                ),
            }
        )
        return context

    def form_valid(self, form):
        div = form.save(commit=False)
        div.routine = self.routine
        div.save()
        messages.success(self.request, "Divisao criada.")
        code = preventive_inspection_routine_url_code(self.routine)
        return redirect(
            "admin-shell:smart-system-inspection-division-detail",
            routine_code=code,
            division_id=div.pk,
        )


class SmartSystemInspectionDivisionDetailView(SmartInspectionRoutineBase, TemplateView):
    """Detalhe + edição da divisão + inclusao/remocao simples de equipamentos."""

    template_name = "admin_shell/smart_system/smart_system_inspection_division_detail.html"
    permission_action = "view"
    routine: PreventiveInspectionRoutine | None = None
    division: InspectionDivision | None = None

    def dispatch(self, request, *args, **kwargs):
        self.routine = lookup_preventive_routine(request, kwargs["routine_code"])
        if self.routine is None:
            raise Http404("Rotina nao encontrada.")
        div_qs = InspectionDivision.objects.filter(routine=self.routine)
        self.division = get_object_or_404(div_qs, pk=kwargs["division_id"])
        if request.method == "POST":
            self.permission_action = "update"
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        code = preventive_inspection_routine_url_code(self.routine)

        if action == "save_division":
            form = InspectionDivisionForm(request.POST, instance=self.division)
            if form.is_valid():
                form.save()
                messages.success(request, "Divisao atualizada.")
            else:
                messages.error(request, "Erro ao salvar divisao.")
            return redirect(
                "admin-shell:smart-system-inspection-division-detail",
                routine_code=code,
                division_id=self.division.pk,
            )

        if action == "add_equipment":
            form = InspectionDivisionEquipmentForm(request.POST, division=self.division, request=request)
            if form.is_valid():
                row = form.save(commit=False)
                row.division = self.division
                try:
                    row.save()
                    messages.success(request, "Equipamento vinculado.")
                except IntegrityError:
                    messages.error(request, "Este equipamento ja esta nesta divisao.")
            else:
                for errs in form.errors.values():
                    messages.error(request, errs.as_text())
            return redirect(
                "admin-shell:smart-system-inspection-division-detail",
                routine_code=code,
                division_id=self.division.pk,
            )

        if action == "remove_equipment":
            link_id = request.POST.get("link_id")
            InspectionDivisionEquipment.objects.filter(
                pk=link_id,
                division=self.division,
            ).delete()
            messages.success(request, "Vinculo removido.")
            return redirect(
                "admin-shell:smart-system-inspection-division-detail",
                routine_code=code,
                division_id=self.division.pk,
            )

        if action == "archive":
            self.division.archived_at = timezone.now()
            self.division.is_active = False
            self.division.save(update_fields=("archived_at", "is_active", "updated_at"))
            messages.success(request, "Divisao arquivada.")
            return redirect(
                "admin-shell:smart-system-inspection-routine-detail",
                routine_code=code,
            )

        if action == "deactivate_only":
            self.division.is_active = False
            self.division.save(update_fields=("is_active", "updated_at"))
            messages.success(request, "Divisao desativada.")
            return redirect(
                "admin-shell:smart-system-inspection-division-detail",
                routine_code=code,
                division_id=self.division.pk,
            )

        return redirect(
            "admin-shell:smart-system-inspection-division-detail",
            routine_code=code,
            division_id=self.division.pk,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = preventive_inspection_routine_url_code(self.routine)
        links = InspectionDivisionEquipment.objects.filter(division=self.division).select_related("asset")
        context.update(
            {
                "routine": self.routine,
                "routine_code": code,
                "division": self.division,
                "division_form": InspectionDivisionForm(instance=self.division),
                "equipment_form": InspectionDivisionEquipmentForm(
                    division=self.division,
                    request=self.request,
                ),
                "equipment_links": links,
                "page_title": self.division.name,
                "page_description": f"Ordem {self.division.sort_order} — Rotina {self.routine.name}",
                "breadcrumbs": self.breadcrumbs_base()
                + [
                    {"label": "Planos rotativos", "url": "admin-shell:smart-system-inspection-routines"},
                    {
                        "label": code,
                        "url": "admin-shell:smart-system-inspection-routine-detail",
                        "route_kwargs": {"routine_code": code},
                    },
                    {"label": self.division.name, "url": None},
                ],
                "current_module_slug": "smart-system",
            }
        )
        return context
