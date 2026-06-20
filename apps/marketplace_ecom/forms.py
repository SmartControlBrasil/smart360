from django import forms

from apps.marketplace_ecom.models import TechnicalProduct


def _lines_to_list(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _list_to_lines(values) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return "\n".join(str(item) for item in values)


def _specs_to_text(specs) -> str:
    if not specs:
        return ""
    if isinstance(specs, dict):
        specs = list(specs.items())
    lines = []
    for item in specs:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            lines.append(f"{item[0]} | {item[1]}")
        elif isinstance(item, dict):
            for key, value in item.items():
                lines.append(f"{key} | {value}")
    return "\n".join(lines)


def _text_to_specs(value: str) -> list[list[str]]:
    specs = []
    for line in _lines_to_list(value):
        if "|" in line:
            label, spec_value = [part.strip() for part in line.split("|", 1)]
            specs.append([label, spec_value])
        else:
            specs.append([line, ""])
    return specs


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


class TechnicalProductAdminForm(forms.ModelForm):
    product_type = forms.CharField(label="tipo de produto", max_length=180, required=False)
    applications = forms.CharField(
        label="aplicações",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Uma aplicação por linha.",
    )
    features = forms.CharField(
        label="recursos principais",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Um recurso por linha.",
    )
    tags = forms.CharField(
        label="tags",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Uma tag por linha.",
    )
    specs = forms.CharField(
        label="ficha técnica",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Formato: Nome | Valor (uma especificação por linha).",
    )
    catalog_image = forms.CharField(
        label="imagem static fallback",
        required=False,
        max_length=300,
        help_text="Caminho static usado quando não houver imagem destacada (ex.: institutional/eitech/img/...).",
    )

    class Meta:
        model = TechnicalProduct
        fields = (
            "title",
            "slug",
            "brand",
            "supplier_name",
            "category",
            "short_description",
            "description",
            "application_area",
            "featured_image",
            "is_active",
            "is_featured",
            "display_order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        metadata = (self.instance.metadata or {}) if self.instance and self.instance.pk else {}
        self.fields["product_type"].initial = metadata.get("product_type", "")
        self.fields["applications"].initial = _list_to_lines(metadata.get("applications", []))
        self.fields["features"].initial = _list_to_lines(metadata.get("features", []))
        self.fields["tags"].initial = _list_to_lines(metadata.get("tags", []))
        self.fields["specs"].initial = _specs_to_text(metadata.get("specs", []))
        self.fields["catalog_image"].initial = metadata.get("catalog_image", "")

    def save(self, commit=True):
        instance = super().save(commit=False)
        metadata = dict(instance.metadata or {})
        metadata.update(
            {
                "product_type": self.cleaned_data.get("product_type") or "Solução técnica",
                "applications": _lines_to_list(self.cleaned_data.get("applications", "")),
                "features": _lines_to_list(self.cleaned_data.get("features", "")),
                "tags": _lines_to_list(self.cleaned_data.get("tags", "")),
                "specs": _text_to_specs(self.cleaned_data.get("specs", "")),
                "catalog_image": self.cleaned_data.get("catalog_image", "").strip(),
                "technical_description": instance.description or instance.short_description,
                "vendor": instance.brand,
                "cta_label": metadata.get("cta_label", "Solicitar orçamento"),
                "lead_interest": metadata.get("lead_interest", f"{instance.brand} - {instance.title}"),
            }
        )
        instance.metadata = metadata
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class TechnicalProductShellForm(TechnicalProductAdminForm):
    """Formulário do catálogo no Admin Shell com widgets estilizados."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.media_library.models import MediaAsset

        widget_classes = {
            "class": "form-control",
        }
        for name, field in self.fields.items():
            widget = field.widget
            attrs = widget.attrs.copy()
            attrs.update(widget_classes)
            if isinstance(widget, forms.Textarea):
                attrs.setdefault("rows", widget.attrs.get("rows", 4))
            elif isinstance(widget, forms.CheckboxInput):
                attrs.pop("class", None)
                attrs["class"] = "form-checkbox"
            field.widget.attrs = attrs

        self.fields["featured_image"].queryset = MediaAsset.objects.filter(is_active=True).order_by("-created_at")
        self.fields["featured_image"].empty_label = "Selecione uma imagem da biblioteca"
