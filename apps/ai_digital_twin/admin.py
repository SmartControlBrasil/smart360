from django.contrib import admin

from .models import DigitalTwin, DigitalTwinProjection, DigitalTwinSignal, DigitalTwinSnapshot


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ("public_id", "twin_type", "company", "site", "asset", "status", "risk_level", "last_projected_at")
    list_filter = ("twin_type", "status", "risk_level", "company")
    search_fields = ("public_id", "current_state_summary", "external_reference", "site__name", "asset__name", "asset__asset_tag")
    autocomplete_fields = ("company", "site", "asset", "contract")
    readonly_fields = ("public_id", "last_projected_at", "created_at", "updated_at")


@admin.register(DigitalTwinSnapshot)
class DigitalTwinSnapshotAdmin(admin.ModelAdmin):
    list_display = ("public_id", "digital_twin", "snapshot_time", "created_at")
    list_filter = ("digital_twin__twin_type", "digital_twin__company")
    search_fields = ("public_id", "digital_twin__public_id")
    autocomplete_fields = ("digital_twin",)
    readonly_fields = ("public_id", "created_at")


@admin.register(DigitalTwinSignal)
class DigitalTwinSignalAdmin(admin.ModelAdmin):
    list_display = ("public_id", "digital_twin", "signal_type", "severity", "is_active", "occurred_at")
    list_filter = ("severity", "is_active", "signal_type", "digital_twin__company")
    search_fields = ("public_id", "signal_type", "title", "summary", "source_reference")
    autocomplete_fields = ("digital_twin",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(DigitalTwinProjection)
class DigitalTwinProjectionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "digital_twin", "projection_type", "projection_status", "updated_at")
    list_filter = ("projection_type", "projection_status", "digital_twin__company")
    search_fields = ("public_id", "digital_twin__public_id")
    autocomplete_fields = ("digital_twin",)
    readonly_fields = ("public_id", "created_at", "updated_at")

