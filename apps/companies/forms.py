"""Formularios Admin Shell para cadastro da empresa SaaS (tenant)."""

from __future__ import annotations

import re

from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.companies.models import Company
from apps.companies.services.saas_registration import company_tax_digits_conflict


User = get_user_model()


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
            "city",
            "state",
            "status",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nome comercial"}),
            "legal_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Razão social"}),
            "tax_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "CNPJ ou identificador fiscal"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Telefone"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://"}),
            "city": forms.TextInput(attrs={"class": "form-input", "placeholder": "Cidade"}),
            "state": forms.TextInput(attrs={"class": "form-input", "placeholder": "UF / estado"}),
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


_WS_RE = re.compile(r"\s+")


class SaasTenantRegistrationForm(forms.Form):
    """
    Cadastro publico inicial: empresa nova + primeiro usuario administrador.
    Persistencia deve ocorrer em transaction.atomic via servico dedicado.
    """

    INPUT = {"class": "auth-input"}

    company_name = forms.CharField(
        label="Nome fantasia / nome da empresa",
        max_length=180,
        strip=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "Nome pela qual a empresa é conhecida"}),
    )
    legal_name = forms.CharField(
        label="Razao social",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "Razão social conforme contrato/documento"}),
    )
    tax_id = forms.CharField(
        label="CNPJ ou documento",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "CNPJ ou outro ID fiscal"}),
    )
    company_email = forms.EmailField(
        label="E-mail da empresa",
        required=False,
        widget=forms.EmailInput(attrs={**INPUT, "placeholder": "contato@empresa.com"}),
    )
    phone_number = forms.CharField(
        label="Telefone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "Telefone comercial"}),
    )
    website = forms.URLField(
        label="Site",
        required=False,
        widget=forms.URLInput(attrs={**INPUT, "placeholder": "https:// ou dominio"}),
    )
    city = forms.CharField(
        label="Cidade",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "Cidade"}),
    )
    state = forms.CharField(
        label="Estado",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "UF ou estado"}),
    )

    admin_name = forms.CharField(
        label="Nome completo",
        max_length=200,
        widget=forms.TextInput(attrs={**INPUT, "placeholder": "Seu nome"}),
    )
    admin_email = forms.EmailField(
        label="E-mail de login",
        widget=forms.EmailInput(attrs={**INPUT, "placeholder": "voce@empresa.com"}),
    )
    password1 = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={**INPUT, "placeholder": "Mínimo 8 caracteres", "autocomplete": "new-password"}),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirmacao de senha",
        strip=False,
        widget=forms.PasswordInput(attrs={**INPUT, "placeholder": "Repita a senha", "autocomplete": "new-password"}),
        min_length=8,
    )

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ja existe uma conta com este e-mail.")
        return email

    def clean_website(self):
        raw = (self.cleaned_data.get("website") or "").strip()
        if not raw:
            return ""
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        return raw

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 is not None and p2 is not None and p1 != p2:
            raise forms.ValidationError("As senhas nao coincidem.")
        return p2

    def clean_tax_id(self):
        tid = self.cleaned_data.get("tax_id") or ""
        return tid.strip()

    def clean_company_email(self):
        value = self.cleaned_data.get("company_email") or ""
        return value.strip().lower()

    def clean_company_name(self):
        name = _WS_RE.sub(" ", (self.cleaned_data.get("company_name") or "").strip())
        if not name:
            raise forms.ValidationError("Informe o nome da empresa.")
        return name

    def clean_admin_name(self):
        name = _WS_RE.sub(" ", (self.cleaned_data.get("admin_name") or "").strip())
        if not name:
            raise forms.ValidationError("Informe seu nome.")
        return name

    def split_admin_name_for_user(self):
        parts = self.cleaned_data["admin_name"].split()
        first = parts[0]
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        return first, last

    def clean(self):
        cleaned = super().clean()
        tax = cleaned.get("tax_id") or ""
        if tax and company_tax_digits_conflict(tax):
            self.add_error("tax_id", "Ja existe uma empresa cadastrada com este documento.")
        return cleaned