from rest_framework import serializers

from ..models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    Checklist,
    ChecklistItem,
    ContractAsset,
    CustomerEquipment,
    EquipmentModel,
    EquipmentModelPart,
    FailureEvent,
    MaintenanceContract,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    QuoteItem,
    RoutePlan,
    ScheduledVisit,
    ServiceQuote,
    ServiceSignature,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    WorkLog,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
)
from ..services.maintenance_service import FailureEventService, ServiceOrderService, WorkLogService
from ..services.maintenance_contract_service import MaintenanceContractService
from ..services.quote_service import ServiceQuoteService
from ..services.tenant_scope import SmartSystemScopeService


class ScopedModelSerializer(serializers.ModelSerializer):
    scoped_relation_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request:
            return
        for field_name in self.scoped_relation_fields:
            field = self.fields.get(field_name)
            if field is None or not hasattr(field, "queryset") or field.queryset is None:
                continue
            field.queryset = SmartSystemScopeService.scope_related_queryset(field.queryset.model, request)


class MaintenanceClientSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company",)

    class Meta:
        model = MaintenanceClient
        fields = (
            "public_id",
            "company",
            "display_name",
            "legal_name",
            "document_number",
            "contact_name",
            "contact_email",
            "contact_phone",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class OperationalSiteSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("maintenance_client",)

    class Meta:
        model = OperationalSite
        fields = (
            "public_id",
            "maintenance_client",
            "name",
            "code",
            "address_line",
            "city",
            "state",
            "zip_code",
            "contact_name",
            "contact_phone",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ("public_id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class AssetSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("operational_site", "category")

    class Meta:
        model = Asset
        fields = (
            "public_id",
            "operational_site",
            "category",
            "asset_tag",
            "name",
            "manufacturer",
            "model",
            "serial_number",
            "voltage",
            "power_rating",
            "installation_date",
            "warranty_until",
            "status",
            "criticality",
            "is_active",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class EquipmentModelPartSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "equipment_model", "part")

    class Meta:
        model = EquipmentModelPart
        fields = (
            "public_id",
            "company",
            "equipment_model",
            "part",
            "quantity_default",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class EquipmentModelSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "category")
    parts = EquipmentModelPartSerializer(many=True, read_only=True)

    class Meta:
        model = EquipmentModel
        fields = (
            "public_id",
            "company",
            "name",
            "category",
            "description",
            "manufacturer",
            "manufacturer_code",
            "equipment_type",
            "is_pmoc_applicable",
            "pmoc_frequency",
            "status",
            "notes",
            "parts",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class CustomerEquipmentSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "site", "equipment_model")

    class Meta:
        model = CustomerEquipment
        fields = (
            "public_id",
            "company",
            "site",
            "equipment_model",
            "display_name",
            "customer_tag",
            "internal_code",
            "serial_number",
            "location",
            "preventive_group",
            "is_pmoc_applicable",
            "status",
            "notes",
            "installed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ChecklistItemSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("checklist",)

    class Meta:
        model = ChecklistItem
        fields = (
            "public_id",
            "checklist",
            "title",
            "description",
            "item_type",
            "ordering",
            "is_required",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ChecklistSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site")
    items = ChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Checklist
        fields = ("public_id", "company", "operational_site", "name", "description", "is_active", "items", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class MaintenancePlanSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "maintenance_contract", "contract_asset", "operational_site", "asset", "category", "checklist")

    class Meta:
        model = MaintenancePlan
        fields = (
            "public_id",
            "company",
            "maintenance_contract",
            "contract_asset",
            "operational_site",
            "asset",
            "category",
            "name",
            "description",
            "frequency_type",
            "frequency_value",
            "estimated_duration_minutes",
            "checklist",
            "is_active",
            "notes",
            "next_due_date",
            "last_generated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "last_generated_at", "created_at", "updated_at")


class ContractAssetSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("contract", "asset")

    class Meta:
        model = ContractAsset
        fields = (
            "public_id",
            "contract",
            "asset",
            "maintenance_frequency",
            "maintenance_frequency_days",
            "estimated_duration_minutes",
            "last_execution",
            "next_execution",
            "is_active",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class MaintenanceContractSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "client", "operational_site")
    covered_assets = ContractAssetSerializer(many=True, required=False)

    class Meta:
        model = MaintenanceContract
        fields = (
            "public_id",
            "company",
            "client",
            "operational_site",
            "contract_number",
            "start_date",
            "end_date",
            "status",
            "billing_frequency",
            "billing_frequency_days",
            "contract_value",
            "next_billing_date",
            "last_billing_date",
            "auto_generate_preventives",
            "notes",
            "metadata",
            "covered_assets",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "last_billing_date", "created_at", "updated_at")

    def create(self, validated_data):
        covered_assets = validated_data.pop("covered_assets", [])
        contract = MaintenanceContractService.create_contract(
            validated_data=validated_data,
            user=self.context["request"].user,
        )
        for item in covered_assets:
            ContractAsset.objects.create(contract=contract, **item)
        return contract

    def update(self, instance, validated_data):
        covered_assets = validated_data.pop("covered_assets", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if covered_assets is not None:
            instance.covered_assets.all().delete()
            for item in covered_assets:
                ContractAsset.objects.create(contract=instance, **item)
        return instance


class ServiceOrderSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("client", "operational_site", "asset", "maintenance_contract", "contract_asset", "maintenance_plan", "assigned_to")

    class Meta:
        model = ServiceOrder
        fields = (
            "public_id",
            "order_number",
            "client",
            "operational_site",
            "asset",
            "maintenance_contract",
            "contract_asset",
            "maintenance_plan",
            "maintenance_type",
            "priority",
            "status",
            "source",
            "title",
            "description",
            "scheduled_start",
            "scheduled_end",
            "opened_at",
            "started_at",
            "completed_at",
            "requested_by",
            "assigned_to",
            "created_by",
            "final_observations",
            "quote_status",
            "quote_required",
            "quote_approved_at",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "order_number", "opened_at", "started_at", "completed_at", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        return ServiceOrderService.create_service_order(user=self.context["request"].user, validated_data=validated_data)

    def update(self, instance, validated_data):
        return ServiceOrderService.update_service_order(service_order=instance, validated_data=validated_data, user=self.context["request"].user)


class ServiceOrderChecklistResponseSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("service_order", "checklist_item")

    class Meta:
        model = ServiceOrderChecklistResponse
        fields = (
            "public_id",
            "service_order",
            "checklist_item",
            "response_boolean",
            "response_text",
            "response_number",
            "response_choice",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class FailureEventSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("asset", "service_order")

    class Meta:
        model = FailureEvent
        fields = (
            "public_id",
            "asset",
            "service_order",
            "detected_at",
            "symptom",
            "probable_cause",
            "root_cause",
            "severity",
            "downtime_minutes",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return FailureEventService.create_failure_event(user=self.context["request"].user, validated_data=validated_data)


class ServiceSignatureSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site", "service_order", "signer_user")

    class Meta:
        model = ServiceSignature
        fields = (
            "public_id",
            "signature_type",
            "signer_role",
            "signer_name",
            "signer_title",
            "signer_document",
            "signer_user",
            "company",
            "operational_site",
            "service_order",
            "report_type",
            "report_reference_code",
            "checklist_execution_reference",
            "signed_at",
            "signature_data",
            "signature_format",
            "acceptance_notes",
            "missing_reason",
            "missing_reason_notes",
            "signed_ip",
            "device_info",
            "request_id",
            "correlation_id",
            "version",
            "is_current",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
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


class AssetHistoryEventSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("asset", "related_service_order", "related_failure_event", "created_by")

    class Meta:
        model = AssetHistoryEvent
        fields = (
            "public_id",
            "asset",
            "event_type",
            "title",
            "description",
            "related_service_order",
            "related_failure_event",
            "occurred_at",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianAvailabilityWindowSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site", "technician", "technician_profile")

    class Meta:
        model = TechnicianAvailabilityWindow
        fields = (
            "public_id",
            "company",
            "operational_site",
            "technician",
            "technician_profile",
            "weekday",
            "blocked_date",
            "start_time",
            "end_time",
            "is_available",
            "max_daily_jobs",
            "max_daily_hours",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianScheduleSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site", "technician", "technician_profile")

    class Meta:
        model = TechnicianSchedule
        fields = (
            "public_id",
            "company",
            "operational_site",
            "technician",
            "technician_profile",
            "date",
            "total_jobs",
            "total_estimated_duration",
            "total_estimated_travel",
            "total_conflicts",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class RoutePlanSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site", "technician", "technician_profile")

    class Meta:
        model = RoutePlan
        fields = (
            "public_id",
            "company",
            "operational_site",
            "technician",
            "technician_profile",
            "date",
            "total_stops",
            "total_estimated_duration",
            "total_estimated_travel",
            "optimization_status",
            "route_summary",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ScheduledVisitSerializer(ScopedModelSerializer):
    scoped_relation_fields = (
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

    class Meta:
        model = ScheduledVisit
        fields = (
            "public_id",
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
            "source_type",
            "title",
            "scheduled_date",
            "scheduled_start",
            "scheduled_end",
            "window_start",
            "window_end",
            "estimated_duration_minutes",
            "estimated_travel_minutes",
            "priority",
            "status",
            "route_order",
            "city",
            "state",
            "location_label",
            "conflict_flags",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class WorkLogSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("service_order", "user")

    class Meta:
        model = WorkLog
        fields = (
            "public_id",
            "service_order",
            "user",
            "started_at",
            "ended_at",
            "labor_minutes",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "labor_minutes", "created_at", "updated_at")

    def create(self, validated_data):
        work_log = super().create(validated_data)
        return WorkLogService.sync_labor_minutes(work_log=work_log)

    def update(self, instance, validated_data):
        work_log = super().update(instance, validated_data)
        return WorkLogService.sync_labor_minutes(work_log=work_log)


class ServiceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDocument
        fields = ("public_id", "service_order", "file", "document_type", "title", "uploaded_by", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class QuoteItemSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("stock_item",)

    class Meta:
        model = QuoteItem
        fields = (
            "public_id",
            "item_type",
            "description",
            "part_reference",
            "stock_item",
            "available_quantity",
            "quantity",
            "unit_price",
            "total_price",
            "estimated_minutes",
            "hourly_rate",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "available_quantity", "total_price", "created_at", "updated_at")


class ServiceQuoteSerializer(ScopedModelSerializer):
    scoped_relation_fields = ("company", "operational_site", "work_order", "asset")
    items = QuoteItemSerializer(many=True)

    class Meta:
        model = ServiceQuote
        fields = (
            "public_id",
            "quote_number",
            "company",
            "operational_site",
            "work_order",
            "asset",
            "status",
            "total_parts",
            "total_labor",
            "total_value",
            "notes",
            "customer_message",
            "sent_at",
            "approved_at",
            "rejected_at",
            "expires_at",
            "approved_by_name",
            "approval_notes",
            "rejection_reason",
            "items",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "public_id",
            "quote_number",
            "total_parts",
            "total_labor",
            "total_value",
            "sent_at",
            "approved_at",
            "rejected_at",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        return ServiceQuoteService.create_quote(
            user=self.context["request"].user,
            validated_data={**validated_data, "items": items},
        )

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        payload = dict(validated_data)
        if items is not None:
            payload["items"] = items
        return ServiceQuoteService.update_quote(
            quote=instance,
            user=self.context["request"].user,
            validated_data=payload,
        )
