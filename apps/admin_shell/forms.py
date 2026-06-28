from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company, Membership, SiteMembership
from apps.companies.services.company_shell_access import user_can_create_saas_company
from apps.companies.services.tenant_scope import TenantScopeService
from apps.smart_system.models import (
    Asset,
    Checklist,
    CustomerEquipment,
    EquipmentModel,
    MaintenanceClient,
    ClientPortalRequest,
    MaintenancePlan,
    OperationalSite,
    ServiceOrder,
    ServiceSignature,
)
from apps.smart_system.services.default_operational_site import ensure_default_operational_site_for_client
from apps.smart_system.services.tenant_scope import SmartSystemScopeService

from .services.smart_system_work_order_create import maintenance_plan_client_and_site


CLIENT_PORTAL_GROUP_CHOICES = [
    ("client-admin", "Administrador do cliente"),
    ("client-manager", "Gestor da unidade"),
    ("requester", "Solicitante"),
    ("client-readonly", "Somente leitura"),
    ("client-portal-only", "Acesso basico ao portal"),
]

CLIENT_PORTAL_GROUP_LABELS = dict(CLIENT_PORTAL_GROUP_CHOICES)
CLIENT_PORTAL_GROUP_NAMES = set(CLIENT_PORTAL_GROUP_LABELS)
CLIENT_PORTAL_GROUP_DESCRIPTIONS = {
    "client-admin": "Administrador do cliente: acesso amplo ao portal do cliente.",
    "client-manager": "Gestor da unidade: pode abrir e acompanhar chamados.",
    "requester": "Solicitante: pode abrir e acompanhar chamados.",
    "client-readonly": "Somente leitura: apenas acompanha chamados e visitas.",
    "client-portal-only": "Acesso basico ao portal: acessa somente o painel basico em /portal/.",
}


class ClientPortalUserForm(forms.Form):
    full_name = forms.CharField(max_length=150, label="Nome completo")
    email = forms.EmailField(label="E-mail")
    company = forms.ModelChoiceField(queryset=Company.objects.none(), label="Empresa")
    site = forms.ModelChoiceField(queryset=OperationalSite.objects.none(), label="Unidade/Site")
    access_level = forms.ChoiceField(
        choices=CLIENT_PORTAL_GROUP_CHOICES,
        label="Nivel de acesso",
        help_text="Gestor da unidade e Solicitante podem abrir chamados. Somente leitura apenas acompanha chamados e visitas.",
    )
    is_active = forms.BooleanField(required=False, initial=True, label="Ativo")
    password = forms.CharField(
        required=False,
        label="Senha inicial ou senha temporaria",
        widget=forms.PasswordInput(render_value=True),
        help_text="Obrigatoria ao criar. Na edicao, deixe em branco para manter a senha atual.",
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.order_by("name")
        self.fields["site"].queryset = OperationalSite.objects.select_related(
            "maintenance_client",
            "maintenance_client__company",
        ).order_by("maintenance_client__display_name", "name")
        if instance is not None and not self.is_bound:
            membership = self._primary_membership(instance)
            site_membership = self._primary_site_membership(instance)
            self.initial.update(
                {
                    "full_name": instance.full_name or instance.display_name or instance.email,
                    "email": instance.email,
                    "company": membership.company if membership else None,
                    "site": site_membership.site if site_membership else None,
                    "access_level": self._access_level_for_user(instance),
                    "is_active": instance.is_active,
                }
            )

    @staticmethod
    def _primary_membership(user):
        return (
            Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            .select_related("company")
            .order_by("-is_primary", "company__name")
            .first()
        )

    @staticmethod
    def _primary_site_membership(user):
        return (
            SiteMembership.objects.filter(user=user, status=SiteMembership.Status.ACTIVE)
            .select_related("site", "site__maintenance_client", "company")
            .order_by("-is_primary", "site__name")
            .first()
        )

    @staticmethod
    def _access_level_for_user(user):
        names = set(user.groups.values_list("name", flat=True))
        for group_name, _label in CLIENT_PORTAL_GROUP_CHOICES:
            if group_name in names:
                return group_name
        return "client-portal-only"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        queryset = get_user_model().objects.filter(email=email)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Ja existe um usuario com este e-mail.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if self.instance is None and not password:
            raise forms.ValidationError("Informe uma senha inicial para o usuario.")
        return password

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get("company")
        site = cleaned.get("site")
        if company and site and site.maintenance_client.company_id != company.id:
            self.add_error("site", "A unidade selecionada nao pertence a empresa escolhida.")
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        full_name = data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        user = self.instance or get_user_model()()
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            raise forms.ValidationError("Usuarios internos nao podem ser alterados por esta tela.")

        user.email = data["email"]
        user.first_name = first_name
        user.last_name = last_name
        user.display_name = full_name
        user.user_type = "client"
        user.is_active = data["is_active"]
        user.is_staff = False
        user.is_superuser = False
        if data.get("password"):
            user.set_password(data["password"])
        elif self.instance is None:
            user.set_unusable_password()
        user.save()

        user.groups.remove(*Group.objects.filter(name__in=CLIENT_PORTAL_GROUP_NAMES))
        selected_group, _created = Group.objects.get_or_create(name=data["access_level"])
        user.groups.add(selected_group)

        company = data["company"]
        site = data["site"]
        Membership.objects.filter(user=user).exclude(company=company).update(
            status=Membership.Status.INACTIVE,
            is_primary=False,
        )
        Membership.objects.update_or_create(
            user=user,
            company=company,
            defaults={"status": Membership.Status.ACTIVE, "is_primary": True},
        )
        SiteMembership.objects.filter(user=user).exclude(site=site).update(
            status=SiteMembership.Status.INACTIVE,
            is_primary=False,
        )
        SiteMembership.objects.update_or_create(
            user=user,
            site=site,
            defaults={"company": company, "status": SiteMembership.Status.ACTIVE, "is_primary": True},
        )
        return user


class ClientPortalRequestForm(forms.ModelForm):
    desired_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = ClientPortalRequest
        fields = [
            "operational_site",
            "asset",
            "category",
            "priority",
            "title",
            "description",
            "contact_name",
            "contact_email",
            "contact_phone",
            "desired_date",
        ]
        widgets = {
            "category": forms.Select(),
            "priority": forms.Select(),
            "title": forms.TextInput(),
            "description": forms.Textarea(attrs={"rows": 5}),
            "contact_name": forms.TextInput(),
            "contact_email": forms.EmailInput(),
            "contact_phone": forms.TextInput(),
        }

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.tenant_context = tenant_context or {}
        if request is not None:
            site_queryset = SmartSystemScopeService.scope_related_queryset(OperationalSite, request).select_related(
                "maintenance_client",
                "maintenance_client__company",
            )
            asset_queryset = SmartSystemScopeService.scope_related_queryset(Asset, request).select_related(
                "operational_site",
                "operational_site__maintenance_client",
                "category",
            )
            active_site = self.tenant_context.get("site")
            if active_site is not None:
                site_queryset = site_queryset.filter(id=active_site.id)
                asset_queryset = asset_queryset.filter(operational_site=active_site)
            self.fields["operational_site"].queryset = site_queryset.order_by("name")
            self.fields["asset"].queryset = asset_queryset.order_by("asset_tag")

        self.fields["operational_site"].required = False
        self.fields["asset"].required = False
        self.fields["operational_site"].label = "Unidade / site"
        self.fields["asset"].label = "Ativo relacionado"
        self.fields["contact_name"].label = "Responsavel local"
        self.fields["contact_email"].label = "Email de contato"
        self.fields["contact_phone"].label = "Telefone de contato"

    def clean(self):
        cleaned_data = super().clean()
        site = cleaned_data.get("operational_site")
        asset = cleaned_data.get("asset")
        active_company = self.tenant_context.get("company")
        active_site = self.tenant_context.get("site")

        if active_company and site and site.maintenance_client.company_id != active_company.id:
            self.add_error("operational_site", "A unidade selecionada nao pertence ao contexto ativo.")
        if asset and active_company and asset.operational_site.maintenance_client.company_id != active_company.id:
            self.add_error("asset", "O ativo selecionado nao pertence ao contexto ativo.")
        if active_site and site and site.id != active_site.id:
            self.add_error("operational_site", "A unidade selecionada nao pertence ao site ativo.")
        if active_site and asset and asset.operational_site_id != active_site.id:
            self.add_error("asset", "O ativo selecionado nao pertence ao site ativo.")
        if site and asset and asset.operational_site_id != site.id:
            self.add_error("asset", "O ativo precisa pertencer a unidade selecionada.")
        if not cleaned_data.get("contact_name") and self.request is not None:
            cleaned_data["contact_name"] = self.request.user.display_name or self.request.user.full_name
        if not cleaned_data.get("contact_email") and self.request is not None:
            cleaned_data["contact_email"] = self.request.user.email
        if cleaned_data.get("desired_date") and cleaned_data["desired_date"] < timezone.localdate():
            self.add_error("desired_date", "A data desejada nao pode estar no passado.")
        return cleaned_data


class CorrectiveServiceOrderForm(forms.Form):
    """Formulario server-side para abrir OS corretiva (Admin Shell)."""

    asset = forms.ModelChoiceField(queryset=Asset.objects.none(), label="Ativo / equipamento")
    title = forms.CharField(max_length=180, label="Titulo / resumo")
    description = forms.CharField(
        required=False,
        label="Descricao",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    priority = forms.ChoiceField(
        label="Prioridade",
        choices=ServiceOrder.Priority.choices,
        initial=ServiceOrder.Priority.MEDIUM,
    )
    assigned_to = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label="Tecnico responsavel",
        empty_label="(sem atribuicao)",
    )
    scheduled_start = forms.DateTimeField(
        required=False,
        label="Data / hora prevista (inicio)",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    scheduled_end = forms.DateTimeField(
        required=False,
        label="Data / hora prevista (fim)",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    notes = forms.CharField(
        required=False,
        label="Observacoes",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    requested_by = forms.CharField(
        required=False,
        max_length=150,
        label="Solicitante",
    )

    def __init__(self, *args, request=None, asset_queryset=None, user_queryset=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        if asset_queryset is not None:
            self.fields["asset"].queryset = asset_queryset
        if user_queryset is not None:
            self.fields["assigned_to"].queryset = user_queryset

    def clean_asset(self):
        asset = self.cleaned_data.get("asset")
        if asset is None:
            raise forms.ValidationError("Selecione um ativo.")
        client = asset.operational_site.maintenance_client
        if client is None:
            raise forms.ValidationError("O ativo selecionado nao possui cliente de manutencao vinculado ao site.")
        company = client.company
        site = asset.operational_site
        if self.request is not None and not SmartSystemScopeService.object_in_scope(
            self.request,
            company=company,
            site=site,
        ):
            raise forms.ValidationError("Este ativo nao esta no escopo permitido para seu usuario.")
        return asset

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("scheduled_start")
        end = cleaned.get("scheduled_end")
        if start and end and end < start:
            self.add_error("scheduled_end", "A data/hora de fim deve ser posterior ao inicio.")
        return cleaned


class PreventiveServiceOrderForm(forms.Form):
    """Geracao de OS preventiva a partir de MaintenancePlan (Admin Shell)."""

    maintenance_plan = forms.ModelChoiceField(queryset=MaintenancePlan.objects.none(), label="Plano preventivo")
    asset = forms.ModelChoiceField(queryset=Asset.objects.none(), label="Ativo / equipamento")
    title = forms.CharField(
        max_length=180,
        required=False,
        label="Titulo / resumo (opcional)",
        help_text="Se em branco, sera usado o nome do plano.",
    )
    scheduled_start = forms.DateTimeField(
        label="Data / hora agendada",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    scheduled_end = forms.DateTimeField(
        required=False,
        label="Data / hora fim prevista",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    priority = forms.ChoiceField(
        label="Prioridade",
        choices=ServiceOrder.Priority.choices,
        initial=ServiceOrder.Priority.MEDIUM,
    )
    assigned_to = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label="Tecnico responsavel",
        empty_label="(sem atribuicao)",
    )
    notes = forms.CharField(
        required=False,
        label="Observacoes",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, request=None, maintenance_plan_queryset=None, asset_queryset=None, user_queryset=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        if maintenance_plan_queryset is not None:
            self.fields["maintenance_plan"].queryset = maintenance_plan_queryset
        if asset_queryset is not None:
            self.fields["asset"].queryset = asset_queryset
        if user_queryset is not None:
            self.fields["assigned_to"].queryset = user_queryset

    def clean_maintenance_plan(self):
        plan = self.cleaned_data.get("maintenance_plan")
        if plan is None:
            raise forms.ValidationError("Selecione um plano preventivo.")
        client, site = maintenance_plan_client_and_site(plan)
        if site is None or client is None:
            raise forms.ValidationError("Este plano nao possui site ou cliente derivavel (vincule site ou ativo ao plano).")
        if self.request is not None and not SmartSystemScopeService.object_in_scope(
            self.request,
            company=client.company,
            site=site,
        ):
            raise forms.ValidationError("Este plano nao esta no escopo permitido para seu usuario.")
        return plan

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("maintenance_plan")
        asset = cleaned.get("asset")
        if not plan or not asset:
            return cleaned
        _client, site = maintenance_plan_client_and_site(plan)
        if plan.asset_id and asset.id != plan.asset_id:
            self.add_error("asset", "O ativo deve ser o mesmo vinculado ao plano preventivo.")
        elif not plan.asset_id and site and asset.operational_site_id != site.id:
            self.add_error("asset", "O ativo deve pertencer ao site operacional do plano.")
        elif plan.asset_id and site and asset.operational_site_id != site.id:
            self.add_error("asset", "O ativo do plano nao pertence ao site operacional esperado; revise o cadastro do plano.")
        start = cleaned.get("scheduled_start")
        end = cleaned.get("scheduled_end")
        if start and end and end < start:
            self.add_error("scheduled_end", "A data/hora de fim deve ser posterior ao inicio.")
        return cleaned


class SmartSystemEquipmentModelForm(forms.ModelForm):
    class Meta:
        model = EquipmentModel
        fields = (
            "company",
            "name",
            "category",
            "description",
            "manufacturer",
            "manufacturer_code",
            "equipment_type",
            "is_pmoc_applicable",
            "pmoc_frequency",
            "status",
            "notes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-input"}),
            "manufacturer_code": forms.TextInput(attrs={"class": "form-input"}),
            "equipment_type": forms.TextInput(attrs={"class": "form-input"}),
            "pmoc_frequency": forms.TextInput(attrs={"class": "form-input"}),
            "company": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_pmoc_applicable": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.tenant_context = tenant_context or {}
        if request is not None:
            allowed_companies = TenantScopeService.get_available_companies(request.user)
            company_ids = [company.id for company in allowed_companies]
            self.fields["company"].queryset = self.fields["company"].queryset.filter(id__in=company_ids)
            self.fields["category"].queryset = self.fields["category"].queryset.order_by("name")
        active_company = self.tenant_context.get("company")
        if active_company:
            self.fields["company"].initial = active_company.id
        self.fields["status"].initial = self.fields["status"].initial or EquipmentModel.Status.ACTIVE

    def clean_company(self):
        company = self.cleaned_data["company"]
        if self.request is not None and not SmartSystemScopeService.object_in_scope(self.request, company=company):
            raise forms.ValidationError("A empresa selecionada nao esta no escopo permitido.")
        return company


class SmartSystemCustomerEquipmentForm(forms.ModelForm):
    class Meta:
        model = CustomerEquipment
        fields = (
            "company",
            "site",
            "equipment_model",
            "display_name",
            "customer_tag",
            "internal_code",
            "serial_number",
            "location",
            "preventive_group",
            "is_pmoc_applicable",
            "status",
            "notes",
            "installed_at",
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "installed_at": forms.DateInput(attrs={"type": "date"}),
            "company": forms.Select(attrs={"class": "form-select"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "equipment_model": forms.Select(attrs={"class": "form-select"}),
            "display_name": forms.TextInput(attrs={"class": "form-input"}),
            "customer_tag": forms.TextInput(attrs={"class": "form-input"}),
            "internal_code": forms.TextInput(attrs={"class": "form-input"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input"}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "preventive_group": forms.TextInput(attrs={"class": "form-input"}),
            "is_pmoc_applicable": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "installed_at": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
        }

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.tenant_context = tenant_context or {}
        if request is not None:
            company_qs = TenantScopeService.get_available_companies(request.user)
            company_ids = [company.id for company in company_qs]
            self.fields["company"].queryset = self.fields["company"].queryset.filter(id__in=company_ids)
            self.fields["site"].queryset = SmartSystemScopeService.scope_related_queryset(OperationalSite, request).order_by("name")
            self.fields["equipment_model"].queryset = SmartSystemScopeService.scope_related_queryset(EquipmentModel, request).order_by("name")
        active_company = self.tenant_context.get("company")
        active_site = self.tenant_context.get("site")
        if active_company:
            self.fields["company"].initial = active_company.id
            self.fields["equipment_model"].queryset = self.fields["equipment_model"].queryset.filter(company=active_company)
            self.fields["site"].queryset = self.fields["site"].queryset.filter(maintenance_client__company=active_company)
        if active_site:
            self.fields["site"].initial = active_site.id
            self.fields["site"].queryset = self.fields["site"].queryset.filter(id=active_site.id)
        self.fields["status"].initial = self.fields["status"].initial or CustomerEquipment.Status.ACTIVE

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get("company")
        site = cleaned.get("site")
        equipment_model = cleaned.get("equipment_model")
        if not company or not site or not equipment_model:
            return cleaned
        if site.maintenance_client.company_id != company.id:
            self.add_error("site", "O site selecionado nao pertence a empresa informada.")
        if equipment_model.company_id != company.id:
            self.add_error("equipment_model", "O modelo selecionado nao pertence a empresa informada.")
        if self.request is not None:
            if not SmartSystemScopeService.object_in_scope(self.request, company=company, site=site):
                self.add_error("site", "O recurso selecionado nao pertence ao escopo ativo.")
        return cleaned


class SmartSystemChecklistForm(forms.Form):
    APPLICATION_CHOICES = (
        ("equipment", "Equipamento"),
        ("equipment_model", "Modelo de equipamento"),
        ("service", "Serviço"),
        ("preventive", "Preventiva"),
        ("general", "Geral"),
    )
    STATUS_CHOICES = (
        ("active", "Ativo"),
        ("inactive", "Inativo"),
    )

    name = forms.CharField(
        max_length=180,
        label="Nome",
        widget=forms.TextInput(attrs={"class": "smart-input", "placeholder": "Nome do checklist"}),
    )
    description = forms.CharField(
        required=False,
        label="Descrição",
        widget=forms.Textarea(attrs={"rows": 4, "class": "smart-textarea", "placeholder": "Descrição breve"}),
    )
    category = forms.CharField(
        max_length=120,
        required=False,
        label="Categoria",
        widget=forms.TextInput(attrs={"class": "smart-input", "placeholder": "Categoria"}),
    )
    application_type = forms.ChoiceField(
        choices=APPLICATION_CHOICES,
        label="Aplicação",
        required=False,
        initial="general",
        widget=forms.Select(attrs={"class": "smart-select"}),
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial="active",
        label="Status",
        required=False,
        widget=forms.Select(attrs={"class": "smart-select"}),
    )


class SmartSystemChecklistItemForm(forms.Form):
    RESPONSE_TYPE_CHOICES = (
        ("ok_nok", "OK / Não OK"),
        ("yes_no", "Sim / Não"),
        ("text", "Texto"),
        ("number", "Número"),
    )

    description = forms.CharField(
        required=False,
        max_length=180,
        label="Descrição do item",
        widget=forms.TextInput(attrs={"class": "smart-input", "placeholder": "Descrição do item"}),
    )
    response_type = forms.ChoiceField(
        required=False,
        choices=RESPONSE_TYPE_CHOICES,
        initial="ok_nok",
        label="Tipo de resposta",
        widget=forms.Select(attrs={"class": "smart-select"}),
    )
    required = forms.BooleanField(
        required=False,
        initial=True,
        label="Obrigatório",
        widget=forms.CheckboxInput(attrs={"class": "smart-checkbox"}),
    )


class SmartSystemMaintenanceClientForm(forms.ModelForm):
    saas_tenant_company = forms.ModelChoiceField(
        label="Empresa SaaS (tenant)",
        queryset=Company.objects.none(),
        required=False,
        help_text="Somente aparece quando voce pode escolher entre varias empresas disponíveis ao seu usuário.",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = MaintenanceClient
        fields = (
            "display_name",
            "document_number",
            "contact_email",
            "contact_phone",
            "is_active",
            "notes",
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4, "class": "form-textarea", "placeholder": "Observações"}),
            "display_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nome do cliente"}),
            "document_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "CNPJ / CPF"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email de contato"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "Telefone"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.tenant_context = tenant_context or {}
        self._resolved_saas_company = None
        instance = kwargs.get("instance")
        avail = TenantScopeService.get_available_companies(request.user) if request else []
        self._saas_available_ids = [c.id for c in avail]
        self.fields["saas_tenant_company"].queryset = (
            Company.objects.filter(id__in=self._saas_available_ids).order_by("name")
            if self._saas_available_ids
            else Company.objects.none()
        )

        show_picker = (
            bool(request)
            and not (instance and instance.pk)
            and (getattr(request.user, "is_superuser", False) or user_can_create_saas_company(request.user))
            and len(avail) > 1
        )

        self.fields["display_name"].label = "Nome"
        self.fields["document_number"].label = "Documento"
        self.fields["contact_email"].label = "Email"
        self.fields["contact_phone"].label = "Telefone"
        self.fields["is_active"].label = "Status ativo"
        self.fields["notes"].label = "Observações"

        self._principal_site_created = False

        if instance and instance.pk:
            del self.fields["saas_tenant_company"]
        elif not show_picker:
            del self.fields["saas_tenant_company"]
        else:
            self.fields["saas_tenant_company"].required = True

    def clean(self):
        cleaned = super().clean()
        if self.instance and self.instance.pk:
            return cleaned
        request = self.request
        avail = TenantScopeService.get_available_companies(request.user) if request else []
        avail_ids = {c.id for c in avail}
        tenant_company = self.tenant_context.get("company")
        picked = cleaned.get("saas_tenant_company")

        if not avail_ids:
            raise forms.ValidationError(
                "Não há empresa SaaS disponível no seu contexto. Cadastre uma empresa assinante "
                "(tenant) antes de registrar clientes operacionais.",
            )

        target = None
        if picked is not None:
            if picked.id not in avail_ids:
                raise forms.ValidationError("Empresa SaaS selecionada inválida para o seu usuário.")
            target = picked
        elif tenant_company is not None and tenant_company.id in avail_ids:
            target = tenant_company
        elif len(avail) == 1:
            target = avail[0]
        else:
            raise forms.ValidationError(
                "Várias empresas estão disponíveis. Por favor use o seletor de contexto (empresa ativa) "
                "na interface ou escolha a empresa SaaS quando o formulário disponibilizar esse campo.",
            )

        self._resolved_saas_company = target
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.pk:
            pass
        else:
            if self._resolved_saas_company is None:
                raise forms.ValidationError("Empresa SaaS não informada.")
            obj.company = self._resolved_saas_company

        self._principal_site_created = False
        if commit:
            creating_new = obj.pk is None
            with transaction.atomic():
                obj.save()
                if creating_new:
                    _, self._principal_site_created = ensure_default_operational_site_for_client(
                        obj,
                        user=self.request.user if self.request else None,
                    )

        return obj


class SmartSystemOperationalSiteForm(forms.ModelForm):
    class Meta:
        model = OperationalSite
        fields = (
            "maintenance_client",
            "name",
            "address_line",
            "city",
            "state",
            "contact_name",
            "contact_phone",
            "is_active",
            "notes",
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "maintenance_client": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "address_line": forms.TextInput(attrs={"class": "form-input"}),
            "city": forms.TextInput(attrs={"class": "form-input"}),
            "state": forms.TextInput(attrs={"class": "form-input"}),
            "contact_name": forms.TextInput(attrs={"class": "form-input"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class SmartSystemPartForm(forms.ModelForm):
    class Meta:
        model = __import__("apps.smart_system.models", fromlist=["Part"]).Part
        fields = (
            "code",
            "name",
            "manufacturer",
            "category",
            "current_stock",
            "minimum_stock",
            "location",
            "primary_supplier",
            "notes",
            "status",
            "operational_site",
        )
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-input"}),
            "category": forms.TextInput(attrs={"class": "form-input"}),
            "current_stock": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
            "primary_supplier": forms.TextInput(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-textarea", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "operational_site": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        if request is not None:
            qs = SmartSystemScopeService.scope_related_queryset(__import__("apps.smart_system.models", fromlist=["OperationalSite"]).OperationalSite, request).order_by("name")
            self.fields["operational_site"].queryset = qs
        # default values handled at model level

    # OperationalSite form initialization handled earlier in class definition


class TechnicianServiceSignatureForm(forms.Form):
    signer_name = forms.CharField(max_length=180, label="Tecnico responsavel")
    signature_data = forms.CharField(widget=forms.HiddenInput())
    acceptance_notes = forms.CharField(
        required=False,
        label="Observacao de encerramento",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_signature_data(self):
        value = (self.cleaned_data.get("signature_data") or "").strip()
        if not value:
            raise forms.ValidationError("A assinatura do tecnico precisa ser registrada.")
        return value


class ClientServiceSignatureForm(forms.Form):
    signer_name = forms.CharField(max_length=180, required=False, label="Nome do representante")
    signer_title = forms.CharField(max_length=120, required=False, label="Cargo / papel")
    signer_document = forms.CharField(max_length=60, required=False, label="Documento")
    signature_data = forms.CharField(required=False, widget=forms.HiddenInput())
    acceptance_notes = forms.CharField(
        required=False,
        label="Observacao de aceite",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    missing_reason = forms.ChoiceField(
        required=False,
        label="Motivo da ausencia de assinatura",
        choices=[("", "Selecione")] + list(ServiceSignature.MissingReason.choices),
    )
    missing_reason_notes = forms.CharField(
        required=False,
        label="Detalhamento da ausencia",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned_data = super().clean()
        signature_data = (cleaned_data.get("signature_data") or "").strip()
        missing_reason = cleaned_data.get("missing_reason") or ""
        signer_name = (cleaned_data.get("signer_name") or "").strip()
        if not signature_data and not missing_reason:
            raise forms.ValidationError("Registre a assinatura do cliente ou informe o motivo da ausencia.")
        if signature_data and not signer_name:
            self.add_error("signer_name", "Informe o nome do cliente ou representante que assinou.")
        return cleaned_data


class ClientQuoteDecisionForm(forms.Form):
    signer_name = forms.CharField(max_length=180, required=False, label="Responsavel pelo aceite")
    notes = forms.CharField(
        required=False,
        label="Observacao",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    rejection_reason = forms.CharField(
        required=False,
        label="Motivo da rejeicao",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
