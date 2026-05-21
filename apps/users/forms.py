from django import forms
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "display_name",
            "phone_number",
            "job_title",
            "department",
            "user_type",
            "is_active",
            "is_staff",
            "is_superuser",
            "is_verified",
        )


class Smart360AuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="E-mail ou usuário",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "class": "auth-input",
                "placeholder": "seuemail@empresa.com",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "auth-input",
                "placeholder": "Digite sua senha",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label="Lembrar-me",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "auth-checkbox"}),
    )

    error_messages = {
        "invalid_login": _(
            "Não foi possível entrar com essas credenciais. Confira os dados e tente novamente."
        ),
        "inactive": _("Esta conta está inativa. Fale com o suporte do SMART360."),
    }
