"""Formularios Admin Shell para cadastro da empresa SaaS (tenant)."""

from __future__ import annotations

from django import forms
from django.utils.text import slugify

from apps.companies.models import Company


class CompanyShellForm(forms.ModelForm):
    """Cadastro/edicao minimos de Company; slug e derivados gerados quando vazio."""

    vincular_usuario_atual = forms.BooleanField(
        required=False,
        initial=False,
        label="Vincular meu usuario a esta empresa (Membership principal)",
        help_text="Somente quando voce pode criar empresas na plataforma. Cria vínculo ativo com is_primary.",
    )

    class Meta:
        model = Company
        fields = (
            "name",
            "legal_name",
            "tax_id",
            "email",
            "phone_number",
            "website",
            "status",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nome comercial"}),
            "legal_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Razão social"}),
            "tax_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "CNPJ ou identificador fiscal"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Telefone"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(
        self,
        *args,
        allow_status_edit: bool = True,
        show_membership_checkbox: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.allow_status_edit = allow_status_edit
        if not allow_status_edit and "status" in self.fields:
            self.fields["status"].disabled = True
        if not show_membership_checkbox and "vincular_usuario_atual" in self.fields:
            del self.fields["vincular_usuario_atual"]

    def _next_unique_slug(self, base_name: str, exclude_pk=None) -> str:
        root = slugify(base_name)[:175] or "empresa"
        candidate = root
        n = 1
        qs = Company.objects.all()
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{root}-{n}"[:180]
            n += 1
        return candidate

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            instance.slug = self._next_unique_slug(instance.name, exclude_pk=instance.pk)
        if commit:
            instance.save()
            self.save_m2m()
        return instance