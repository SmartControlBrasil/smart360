from django import forms

from .models import LiviaKnowledgeItem


class LiviaChatForm(forms.Form):
    message = forms.CharField(max_length=2000)
    session_key = forms.CharField(max_length=120, required=False)
    source_page = forms.CharField(max_length=255, required=False)


class LiviaKnowledgeItemForm(forms.ModelForm):
    class Meta:
        model = LiviaKnowledgeItem
        fields = ("title", "slug", "category", "content", "keywords", "is_active", "priority")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "keywords": forms.Textarea(attrs={"rows": 3}),
        }
