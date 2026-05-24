from __future__ import annotations

from django import forms

from apps.companies.models import Company
from apps.smart_system.models import (
    Asset,
    Checklist,
    InspectionDivision,
    InspectionDivisionEquipment,
    OperationalSite,
    PreventiveInspectionRoutine,
)
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


class PreventiveInspectionRoutineForm(forms.ModelForm):
    class Meta:
        model = PreventiveInspectionRoutine
        fields = ("company", "operational_site", "checklist", "name", "description", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["operational_site"].label = "Unidade / Local operacional"
        if request is not None:
            allowed = SmartSystemScopeService.get_allowed_company_ids(request.user)
            self.fields["company"].queryset = Company.objects.filter(id__in=allowed).order_by("name")
            site_qs = SmartSystemScopeService.scope_related_queryset(OperationalSite, request)
            self.fields["operational_site"].queryset = site_qs
            ck_qs = SmartSystemScopeService.scope_queryset(Checklist.objects.all(), request)
            self.fields["checklist"].queryset = ck_qs.select_related("company", "operational_site")

    def clean(self):
        data = super().clean()
        site = data.get("operational_site")
        company = data.get("company")
        checklist = data.get("checklist")
        if site and company and site.maintenance_client.company_id != company.id:
            raise forms.ValidationError("A unidade selecionada não pertence à empresa informada.")
        if checklist and site:
            if checklist.operational_site_id and checklist.operational_site_id != site.id:
                raise forms.ValidationError("O checklist está vinculado a outra unidade operacional.")
            if (
                checklist.company_id
                and site.maintenance_client.company_id
                and checklist.company_id != site.maintenance_client.company_id
            ):
                raise forms.ValidationError("O checklist não pertence ao mesmo cliente/empresa da unidade.")
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        site = instance.operational_site
        if site_id := getattr(site, "id", None):
            client = OperationalSite.objects.select_related("maintenance_client").get(pk=site_id).maintenance_client
            if client.company_id:
                instance.company_id = client.company_id
        elif not instance.company_id and self.cleaned_data.get("company"):
            instance.company = self.cleaned_data["company"]

        if commit:
            instance.save()
        return instance


class InspectionDivisionForm(forms.ModelForm):
    class Meta:
        model = InspectionDivision
        fields = ("name", "sort_order", "is_active")


class InspectionDivisionEquipmentForm(forms.ModelForm):
    class Meta:
        model = InspectionDivisionEquipment
        fields = ("asset", "always_include_in_visit")

    def __init__(self, *args, division: InspectionDivision, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._division = division
        routine = division.routine
        site_id = routine.operational_site_id
        base = Asset.objects.filter(operational_site_id=site_id, is_active=True)
        if request is not None:
            base = SmartSystemScopeService.scope_queryset(base, request)
        self.fields["asset"].queryset = base.select_related("operational_site", "category")

    def clean_asset(self):
        asset = self.cleaned_data["asset"]
        if asset.operational_site_id != self._division.routine.operational_site_id:
            raise forms.ValidationError("O equipamento precisa pertencer à mesma unidade da rotina.")
        return asset
