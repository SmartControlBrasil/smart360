from django.contrib import admin

from .models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    Checklist,
    ChecklistItem,
    ClientPortalRequest,
    ContractAsset,
    CustomerEquipment,
    EquipmentModel,
    EquipmentModelPart,
    FieldExecutionSnapshot,
    FieldSyncOperation,
    FailureEvent,
    InspectionDivision,
    InspectionDivisionEquipment,
    MaintenanceContract,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    Part,
    PartAssetLink,
    QuoteItem,
    RoutePlan,
    ScheduledVisit,
    ServiceQuote,
    ServiceSignature,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
    WorkLog,
    PreventiveInspectionRoutine,
)


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0


class ServiceOrderChecklistResponseInline(admin.TabularInline):
    model = ServiceOrderChecklistResponse
    extra = 0


class WorkLogInline(admin.TabularInline):
    model = WorkLog
    extra = 0
    autocomplete_fields = ("user",)


class ServiceDocumentInline(admin.TabularInline):
    model = ServiceDocument
    extra = 0
    autocomplete_fields = ("uploaded_by",)


class ServiceSignatureInline(admin.TabularInline):
    model = ServiceSignature
    extra = 0
    autocomplete_fields = ("signer_user",)
    readonly_fields = ("public_id", "signed_at", "request_id", "correlation_id", "version", "is_current", "created_at", "updated_at")


class PartAssetLinkInline(admin.TabularInline):
    model = PartAssetLink
    extra = 0


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    autocomplete_fields = ("service_order", "performed_by")


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    autocomplete_fields = ("stock_item",)


class ContractAssetInline(admin.TabularInline):
    model = ContractAsset
    extra = 0
    autocomplete_fields = ("asset",)


class EquipmentModelPartInline(admin.TabularInline):
    model = EquipmentModelPart
    extra = 0
    autocomplete_fields = ("part", "company")


@admin.register(MaintenanceClient)
class MaintenanceClientAdmin(admin.ModelAdmin):
    list_display = ("display_name", "company", "contact_name", "contact_phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("display_name", "legal_name", "document_number", "contact_name", "contact_email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company",)


@admin.register(OperationalSite)
class OperationalSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "maintenance_client", "code", "city", "state", "is_active")
    list_filter = ("is_active", "state")
    search_fields = ("name", "code", "city", "state", "contact_name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("maintenance_client",)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "operational_site", "category", "status", "criticality", "is_active")
    list_filter = ("status", "criticality", "category", "is_active")
    search_fields = ("asset_tag", "name", "serial_number", "manufacturer", "model")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("operational_site", "category")


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (ChecklistItemInline,)


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("title", "checklist", "item_type", "ordering", "is_required", "is_active")
    list_filter = ("item_type", "is_required", "is_active")
    search_fields = ("title", "description", "checklist__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("checklist",)


class InspectionDivisionInline(admin.TabularInline):
    model = InspectionDivision
    extra = 0
    fields = ("name", "sort_order", "is_active", "archived_at")
    ordering = ("sort_order", "id")


@admin.register(PreventiveInspectionRoutine)
class PreventiveInspectionRoutineAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "operational_site", "checklist", "next_division", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site", "checklist")
    inlines = (InspectionDivisionInline,)
    fieldsets = (
        (None, {"fields": ("public_id", "company", "operational_site", "checklist", "name", "description", "is_active")}),
        ("Rotacao", {"fields": ("next_division",)}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "next_division":
            obj_id = request.resolver_match.kwargs.get("object_id") if request.resolver_match else None
            if obj_id:
                kwargs["queryset"] = InspectionDivision.objects.filter(routine_id=obj_id).order_by(
                    "sort_order", "id"
                )
            else:
                kwargs["queryset"] = InspectionDivision.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InspectionDivisionEquipmentInline(admin.TabularInline):
    model = InspectionDivisionEquipment
    extra = 0
    autocomplete_fields = ("asset",)


@admin.register(InspectionDivision)
class InspectionDivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "routine", "sort_order", "is_active", "archived_at", "updated_at")
    list_filter = ("is_active", "routine__operational_site")
    search_fields = ("name", "routine__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("routine",)
    inlines = (InspectionDivisionEquipmentInline,)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InspectionDivisionEquipment)
class InspectionDivisionEquipmentAdmin(admin.ModelAdmin):
    list_display = ("division", "asset", "always_include_in_visit", "created_at")
    search_fields = ("division__name", "asset__asset_tag", "asset__name")
    autocomplete_fields = ("division", "asset")


@admin.register(MaintenancePlan)
class MaintenancePlanAdmin(admin.ModelAdmin):
    list_display = ("name", "asset", "category", "frequency_type", "frequency_value", "is_active", "next_due_date")
    list_filter = ("frequency_type", "is_active")
    search_fields = ("name", "description", "notes")
    readonly_fields = ("public_id", "last_generated_at", "created_at", "updated_at")
    autocomplete_fields = ("maintenance_contract", "contract_asset", "asset", "category", "checklist")


@admin.register(MaintenanceContract)
class MaintenanceContractAdmin(admin.ModelAdmin):
    list_display = ("contract_number", "company", "client", "operational_site", "status", "billing_frequency", "contract_value", "next_billing_date")
    list_filter = ("status", "billing_frequency", "company", "operational_site", "auto_generate_preventives")
    search_fields = ("contract_number", "client__display_name", "client__legal_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "client", "operational_site")
    inlines = (ContractAssetInline,)


@admin.register(ContractAsset)
class ContractAssetAdmin(admin.ModelAdmin):
    list_display = ("contract", "asset", "maintenance_frequency", "next_execution", "last_execution", "is_active")
    list_filter = ("maintenance_frequency", "is_active", "contract__company")
    search_fields = ("contract__contract_number", "asset__asset_tag", "asset__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("contract", "asset")


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "client", "operational_site", "asset", "maintenance_type", "priority", "status", "assigned_to")
    list_filter = ("maintenance_type", "priority", "status", "source")
    search_fields = ("order_number", "title", "description", "requested_by", "client__display_name")
    readonly_fields = ("public_id", "order_number", "opened_at", "started_at", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("client", "operational_site", "asset", "maintenance_contract", "contract_asset", "maintenance_plan", "assigned_to", "created_by")
    inlines = (ServiceOrderChecklistResponseInline, WorkLogInline, ServiceDocumentInline, ServiceSignatureInline)


@admin.register(ServiceOrderChecklistResponse)
class ServiceOrderChecklistResponseAdmin(admin.ModelAdmin):
    list_display = ("service_order", "checklist_item", "response_boolean", "response_number", "response_choice")
    list_filter = ("checklist_item__item_type",)
    search_fields = ("service_order__order_number", "checklist_item__title", "response_text", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("service_order", "checklist_item")


@admin.register(FailureEvent)
class FailureEventAdmin(admin.ModelAdmin):
    list_display = ("asset", "severity", "status", "detected_at", "downtime_minutes")
    list_filter = ("severity", "status")
    search_fields = ("asset__asset_tag", "symptom", "probable_cause", "root_cause")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("asset", "service_order")


@admin.register(AssetHistoryEvent)
class AssetHistoryEventAdmin(admin.ModelAdmin):
    list_display = ("asset", "event_type", "title", "occurred_at", "created_by")
    list_filter = ("event_type",)
    search_fields = ("asset__asset_tag", "title", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("asset", "related_service_order", "related_failure_event", "created_by")


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("service_order", "user", "started_at", "ended_at", "labor_minutes")
    list_filter = ("user",)
    search_fields = ("service_order__order_number", "user__email", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("service_order", "user")


@admin.register(ServiceDocument)
class ServiceDocumentAdmin(admin.ModelAdmin):
    list_display = ("service_order", "title", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type",)
    search_fields = ("service_order__order_number", "title", "uploaded_by__email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("service_order", "uploaded_by")


@admin.register(ServiceSignature)
class ServiceSignatureAdmin(admin.ModelAdmin):
    list_display = (
        "signature_type",
        "signer_role",
        "signer_name",
        "company",
        "operational_site",
        "service_order",
        "signed_at",
        "is_current",
    )
    list_filter = ("signature_type", "signer_role", "company", "operational_site", "is_current", "signed_at")
    search_fields = ("signer_name", "signer_document", "service_order__order_number", "report_reference_code")
    readonly_fields = (
        "public_id",
        "signed_at",
        "signed_ip",
        "device_info",
        "request_id",
        "correlation_id",
        "version",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("company", "operational_site", "service_order", "signer_user")


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "operational_site", "current_stock", "minimum_stock", "status")
    list_filter = ("company", "operational_site", "status", "category")
    search_fields = ("code", "name", "manufacturer", "model", "primary_supplier", "location")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site")
    inlines = (PartAssetLinkInline, StockMovementInline)


@admin.register(PartAssetLink)
class PartAssetLinkAdmin(admin.ModelAdmin):
    list_display = ("part", "asset", "quantity_recommended", "updated_at")
    list_filter = ("asset__operational_site", "asset__category")
    search_fields = ("part__code", "part__name", "asset__asset_tag", "asset__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("part", "asset")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("part", "movement_type", "quantity", "company", "operational_site", "service_order", "performed_by", "occurred_at")
    list_filter = ("movement_type", "company", "operational_site", "occurred_at")
    search_fields = ("part__code", "part__name", "service_order__order_number", "reference_type", "reference_id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("part", "company", "operational_site", "service_order", "performed_by")


@admin.register(ServiceQuote)
class ServiceQuoteAdmin(admin.ModelAdmin):
    list_display = ("quote_number", "company", "operational_site", "work_order", "status", "total_value", "sent_at", "approved_at")
    list_filter = ("status", "company", "operational_site")
    search_fields = ("quote_number", "work_order__order_number", "approved_by_name", "notes")
    readonly_fields = ("public_id", "quote_number", "total_parts", "total_labor", "total_value", "sent_at", "approved_at", "rejected_at", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site", "work_order", "asset", "approved_by_user", "created_by", "updated_by")
    inlines = (QuoteItemInline,)


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ("quote", "item_type", "description", "quantity", "unit_price", "total_price", "stock_item")
    list_filter = ("item_type", "quote__company")
    search_fields = ("quote__quote_number", "description", "part_reference", "stock_item__code", "stock_item__name")
    readonly_fields = ("public_id", "available_quantity", "total_price", "created_at", "updated_at")
    autocomplete_fields = ("quote", "stock_item")


@admin.register(ClientPortalRequest)
class ClientPortalRequestAdmin(admin.ModelAdmin):
    list_display = ("protocol_number", "company", "operational_site", "asset", "category", "priority", "status", "requester")
    list_filter = ("company", "operational_site", "category", "priority", "status")
    search_fields = ("protocol_number", "title", "description", "contact_name", "contact_email")
    readonly_fields = ("public_id", "protocol_number", "created_at", "updated_at", "last_customer_update_at")
    autocomplete_fields = ("company", "operational_site", "asset", "requester", "related_service_order")


@admin.register(FieldExecutionSnapshot)
class FieldExecutionSnapshotAdmin(admin.ModelAdmin):
    list_display = ("service_order", "technician", "sync_state", "progress", "last_server_sync_at", "updated_at")
    list_filter = ("sync_state", "company", "operational_site")
    search_fields = ("service_order__order_number", "technician__email", "last_client_operation_id")
    readonly_fields = ("public_id", "created_at", "updated_at", "last_server_sync_at")
    autocomplete_fields = ("company", "operational_site", "service_order", "technician")


@admin.register(FieldSyncOperation)
class FieldSyncOperationAdmin(admin.ModelAdmin):
    list_display = ("client_operation_id", "action_type", "service_order", "technician", "status", "attempts", "processed_at")
    list_filter = ("status", "action_type", "company", "operational_site")
    search_fields = ("client_operation_id", "service_order__order_number", "technician__email", "error_code")
    readonly_fields = ("public_id", "created_at", "updated_at", "processed_at")
    autocomplete_fields = ("company", "operational_site", "service_order", "technician")


@admin.register(TechnicianAvailabilityWindow)
class TechnicianAvailabilityWindowAdmin(admin.ModelAdmin):
    list_display = ("technician", "company", "operational_site", "weekday", "blocked_date", "is_available", "max_daily_jobs", "max_daily_hours")
    list_filter = ("company", "operational_site", "is_available", "weekday")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site", "technician", "technician_profile")


@admin.register(TechnicianSchedule)
class TechnicianScheduleAdmin(admin.ModelAdmin):
    list_display = ("technician", "company", "operational_site", "date", "total_jobs", "total_estimated_duration", "total_estimated_travel", "total_conflicts")
    list_filter = ("company", "operational_site", "date")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site", "technician", "technician_profile")


@admin.register(RoutePlan)
class RoutePlanAdmin(admin.ModelAdmin):
    list_display = ("technician", "company", "operational_site", "date", "total_stops", "total_estimated_duration", "total_estimated_travel", "optimization_status")
    list_filter = ("company", "operational_site", "optimization_status", "date")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "operational_site", "technician", "technician_profile")


@admin.register(ScheduledVisit)
class ScheduledVisitAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "operational_site", "technician", "scheduled_date", "scheduled_start", "priority", "status", "route_order")
    list_filter = ("company", "operational_site", "source_type", "status", "priority", "scheduled_date")
    search_fields = ("title", "location_label", "city", "state", "work_order__order_number")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = (
        "company",
        "operational_site",
        "asset",
        "work_order",
        "service_assignment",
        "maintenance_plan",
        "technician_schedule",
        "route_plan",
        "technician",
        "technician_profile",
    )


@admin.register(EquipmentModel)
class EquipmentModelAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "category", "manufacturer", "equipment_type", "is_pmoc_applicable", "status")
    list_filter = ("company", "category", "status", "is_pmoc_applicable")
    search_fields = ("name", "manufacturer", "manufacturer_code", "equipment_type", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "category")
    inlines = (EquipmentModelPartInline,)


@admin.register(EquipmentModelPart)
class EquipmentModelPartAdmin(admin.ModelAdmin):
    list_display = ("equipment_model", "part", "company", "quantity_default", "updated_at")
    list_filter = ("company", "equipment_model__category")
    search_fields = ("equipment_model__name", "part__name", "part__code", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "equipment_model", "part")


@admin.register(CustomerEquipment)
class CustomerEquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "customer_tag",
        "display_name",
        "equipment_model",
        "company",
        "site",
        "preventive_group",
        "is_pmoc_applicable",
        "status",
    )
    list_filter = ("company", "site", "status", "preventive_group", "is_pmoc_applicable")
    search_fields = ("customer_tag", "display_name", "internal_code", "serial_number", "location", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("company", "site", "equipment_model")
