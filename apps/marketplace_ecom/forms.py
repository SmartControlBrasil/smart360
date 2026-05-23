from django import forms


class MarketplaceQuoteRequestForm(forms.Form):
    name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Seu nome",
                "autocomplete": "name",
            }
        ),
    )
    company = forms.CharField(
        label="Empresa",
        max_length=180,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Empresa ou organização",
                "autocomplete": "organization",
            }
        ),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "seu@email.com",
                "autocomplete": "email",
            }
        ),
    )
    phone = forms.CharField(
        label="Telefone",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Telefone ou WhatsApp",
                "autocomplete": "tel",
            }
        ),
    )
    city = forms.CharField(
        label="Cidade",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Cidade",
                "autocomplete": "address-level2",
            }
        ),
    )
    message = forms.CharField(
        label="Mensagem",
        max_length=1200,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Conte rapidamente sua necessidade, quantidade estimada ou contexto do projeto.",
                "rows": 5,
            }
        ),
    )
