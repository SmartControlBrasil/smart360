from django import forms

from apps.smart_system.models import Asset, OperationalSite, ServiceOrder

from .services import allowed_assets, allowed_sites


class ClientServiceOrderForm(forms.Form):
    operational_site = forms.ModelChoiceField(
        label="Unidade/site",
        queryset=OperationalSite.objects.none(),
        required=True,
        empty_label="Selecione a unidade",
    )
    asset = forms.ModelChoiceField(
        label="Equipamento/ativo",
        queryset=Asset.objects.none(),
        required=False,
        empty_label="Sem equipamento específico",
    )
    priority = forms.ChoiceField(
        label="Prioridade",
        choices=ServiceOrder.Priority.choices,
        required=True,
        initial=ServiceOrder.Priority.MEDIUM,
    )
    description = forms.CharField(
        label="Descrição",
        widget=forms.Textarea(attrs={"rows": 5}),
        required=True,
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        if request is None:
            return

        sites = allowed_sites(request).filter(is_active=True).order_by("maintenance_client__display_name", "name")
        assets = allowed_assets(request).filter(is_active=True).order_by("operational_site__name", "asset_tag")
        self.fields["operational_site"].queryset = sites
        self.fields["asset"].queryset = assets

    def clean_asset(self):
        asset = self.cleaned_data.get("asset")
        site = self.cleaned_data.get("operational_site")
        if asset and site and asset.operational_site_id != site.id:
            raise forms.ValidationError("Selecione um equipamento da unidade escolhida.")
        return asset
