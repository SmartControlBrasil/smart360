from django import forms

from apps.companies.models import Company

from .models import Niche, SiteProjectIntake, Template
from .services.template_package import format_template_choice_label


class SiteOrderCreateForm(forms.Form):
    niche = forms.ModelChoiceField(
        label="Nicho",
        queryset=Niche.objects.none(),
        required=True,
    )
    selected_template = forms.ModelChoiceField(
        label="Pacote (template)",
        queryset=Template.objects.none(),
        required=False,
        help_text="Opcional: escolha o pacote comercial vinculado ao template. Deixe em branco para usar a recomendacao automatica pelo nicho.",
    )
    company = forms.ModelChoiceField(
        label="Empresa vinculada",
        queryset=Company.objects.none(),
        required=False,
    )
    client_name = forms.CharField(label="Nome do cliente", max_length=180, required=False)
    client_phone = forms.CharField(label="Telefone", max_length=30, required=False)
    client_email = forms.EmailField(label="Email", required=False)
    client_company_name = forms.CharField(label="Empresa", max_length=180, required=False)
    notes = forms.CharField(
        label="Observacoes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, request=None, tenant_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.tenant_context = tenant_context or {}
        self.fields["niche"].queryset = Niche.objects.filter(is_active=True).order_by("name")
        self.fields["selected_template"].queryset = (
            Template.objects.filter(is_active=True, status=Template.Status.READY)
            .select_related("niche")
            .order_by("niche__name", "name")
        )
        self.fields["selected_template"].label_from_instance = format_template_choice_label
        company_queryset = Company.objects.filter(status=Company.Status.ACTIVE).order_by("name")
        active_company = self.tenant_context.get("company")
        if active_company is not None and not getattr(request.user, "is_superuser", False):
            company_queryset = company_queryset.filter(id=active_company.id)
            self.fields["company"].initial = active_company
        self.fields["company"].queryset = company_queryset
        self.fields["client_name"].initial = getattr(request.user, "full_name", "") if request else ""
        self.fields["client_email"].initial = getattr(request.user, "email", "") if request else ""

    def clean(self):
        cleaned_data = super().clean()
        niche = cleaned_data.get("niche")
        selected_template = cleaned_data.get("selected_template")
        if selected_template and niche and selected_template.niche_id != niche.id:
            self.add_error("selected_template", "O template selecionado precisa pertencer ao nicho escolhido.")
        return cleaned_data

    def build_order_payload(self):
        return {
            "company": self.cleaned_data.get("company"),
            "niche": self.cleaned_data["niche"],
            "selected_template": self.cleaned_data.get("selected_template"),
            "notes": self.cleaned_data.get("notes") or "",
            "metadata": {
                "client_name": self.cleaned_data.get("client_name") or "",
                "client_phone": self.cleaned_data.get("client_phone") or "",
                "client_email": self.cleaned_data.get("client_email") or "",
                "client_company_name": self.cleaned_data.get("client_company_name") or "",
            },
        }


class SiteProjectIntakeForm(forms.ModelForm):
    main_services_text = forms.CharField(
        label="Servicos principais",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Informe um item por linha.",
    )
    social_links = forms.CharField(
        label="Redes sociais",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Use uma URL por linha. Instagram e Facebook sao identificados automaticamente.",
    )
    photo_gallery_text = forms.CharField(
        label="Gallery URLs",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Informe uma URL por linha.",
    )

    class Meta:
        model = SiteProjectIntake
        fields = [
            "company_name",
            "phone",
            "whatsapp",
            "address",
            "city",
            "state",
            "business_description",
            "logo_url",
            "notes",
        ]
        labels = {
            "company_name": "Empresa",
            "phone": "Telefone",
            "whatsapp": "WhatsApp",
            "address": "Endereco",
            "city": "Cidade",
            "state": "Estado",
            "business_description": "Descricao do negocio",
            "logo_url": "Logo URL",
            "notes": "Observacoes adicionais",
        }
        widgets = {
            "business_description": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, order=None, **kwargs):
        self.order = order
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["main_services_text"].initial = "\n".join(self.instance.main_services or [])
            social_links = [self.instance.instagram, self.instance.facebook]
            self.fields["social_links"].initial = "\n".join([link for link in social_links if link])
            self.fields["photo_gallery_text"].initial = "\n".join(self.instance.photo_gallery or [])
        elif order is not None:
            metadata = order.metadata or {}
            self.fields["company_name"].initial = metadata.get("client_company_name") or getattr(order.company, "name", "")
            self.fields["phone"].initial = metadata.get("client_phone") or ""

    def _split_lines(self, value):
        return [line.strip() for line in (value or "").splitlines() if line.strip()]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.order is not None:
            instance.site_order = self.order
        instance.main_services = self._split_lines(self.cleaned_data.get("main_services_text"))
        social_links = self._split_lines(self.cleaned_data.get("social_links"))
        instance.instagram = next((link for link in social_links if "instagram." in link.lower()), "")
        instance.facebook = next((link for link in social_links if "facebook." in link.lower()), "")
        instance.photo_gallery = self._split_lines(self.cleaned_data.get("photo_gallery_text"))
        if commit:
            instance.save()
        return instance
