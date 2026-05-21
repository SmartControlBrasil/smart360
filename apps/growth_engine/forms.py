from django import forms

from .models import CommercialProposal


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
