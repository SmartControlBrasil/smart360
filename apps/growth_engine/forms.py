from django import forms

from .models import CommercialProposal, Lead, LeadInteraction


class MarketplaceLeadInteractionForm(forms.ModelForm):
    class Meta:
        model = LeadInteraction
        fields = ("interaction_type", "channel", "summary")
        labels = {
            "interaction_type": "Tipo da interação",
            "channel": "Canal",
            "summary": "Observação / resumo",
        }
        widgets = {"summary": forms.Textarea(attrs={"rows": 4, "class": "smart-textarea"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("interaction_type", "channel"):
            self.fields[name].widget.attrs.setdefault("class", "smart-select")
        self.fields["summary"].widget.attrs.setdefault("class", "smart-textarea")


class MarketplaceLeadStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Lead.Status.choices, label="Status do lead")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.setdefault("class", "smart-select")


class CommercialProposalForm(forms.ModelForm):
    class Meta:
        model = CommercialProposal
        fields = (
            "company_name",
            "contact_name",
            "email",
            "phone",
            "service_interest",
            "urgency",
            "origin",
            "summary",
            "scope",
            "customer_message",
            "total_value",
        )
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
            "scope": forms.Textarea(attrs={"rows": 5}),
            "customer_message": forms.Textarea(attrs={"rows": 4}),
        }


class OperationalForwardNoteForm(forms.Form):
    """Observação ao registrar encaminhamento operacional da proposta aprovada."""

    note = forms.CharField(
        label="Observação de encaminhamento operacional",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "form-textarea",
                "placeholder": "Escopo operacional inicial, SLA informado ao cliente, ponto focal interno etc.",
                "aria-describedby": "growth-operational-forward-hint",
            }
        ),
        min_length=3,
        max_length=8000,
    )
