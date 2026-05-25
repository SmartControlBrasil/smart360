from django import forms


USAGE_TYPE_CHOICES = (
    ("presente", "Presente"),
    ("empresa", "Empresa / corporativo"),
    ("escola", "Escola / turma"),
    ("igreja", "Igreja / comunidade"),
    ("evento", "Evento / celebração"),
)

ARTWORK_NEED_CHOICES = (
    ("nao_preciso", "Já tenho arte pronta"),
    ("adaptacao_simples", "Preciso apenas de adaptação simples"),
    ("criacao", "Preciso criar arte com vocês"),
    ("nao_sei", "Ainda não sei — quero orientação"),
)


class BaseLeadForm(forms.Form):
    customer_name = forms.CharField(
        label="Nome completo",
        max_length=180,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Seu nome*"}),
    )
    whatsapp = forms.CharField(
        label="WhatsApp (com DDD)",
        max_length=32,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Ex.: (11) 99999-0000"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "style-1", "placeholder": "nome@email.com*"}),
    )
    quantity = forms.IntegerField(
        label="Quantidade desejada",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "style-1", "placeholder": "1"}),
    )
    message_or_phrase = forms.CharField(
        label="Mensagem / frase / ideia principal",
        widget=forms.Textarea(attrs={"class": "style-1", "rows": 4, "placeholder": "O que você quer estampar ou transmitir?*"}),
    )
    observations = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={"class": "style-1", "rows": 3, "placeholder": "Cores preferidas, tamanhos, formato do evento…"}),
    )
    usage_type = forms.ChoiceField(
        label="Tipo de uso",
        choices=USAGE_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "style-1"}),
    )
    artwork_need = forms.ChoiceField(
        label="Precisa de arte gráfica?",
        choices=ARTWORK_NEED_CHOICES,
        widget=forms.Select(attrs={"class": "style-1"}),
    )


class PersonalizationLeadForm(BaseLeadForm):
    product_slug = forms.CharField(required=False, widget=forms.HiddenInput())
    partner_slug = forms.CharField(required=False, widget=forms.HiddenInput())


class B2BQuoteLeadForm(BaseLeadForm):
    organization_name = forms.CharField(
        label="Empresa ou instituição",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Razão social ou nome fictício"}),
    )
    job_title_or_area = forms.CharField(
        label="Cargo / área",
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Compras, marketing, RH…"}),
    )


class ContactForm(forms.Form):
    customer_name = forms.CharField(
        label="",
        max_length=180,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Seu nome"}),
    )
    email = forms.EmailField(
        label="",
        widget=forms.EmailInput(attrs={"class": "style-1", "placeholder": "seuemail@email.com"}),
    )
    whatsapp = forms.CharField(
        label="",
        required=False,
        max_length=32,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "(11) 99999-9999"}),
    )
    subject = forms.CharField(
        label="",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "style-1", "placeholder": "Como podemos ajudar?"}),
    )
    message = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={"class": "style-1", "rows": 4, "placeholder": "Conte sua ideia, pedido, prazo ou dúvida"}),
    )
