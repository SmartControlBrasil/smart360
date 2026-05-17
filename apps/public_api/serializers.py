from rest_framework import serializers

from apps.companies.models import Company
from apps.smart_system.models import (
    Asset,
    Checklist,
    ChecklistItem,
    FailureEvent,
    MaintenancePlan,
    OperationalSite,
    Part,
    PartAssetLink,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
)
from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
)
from apps.marketplace_technicians.services.marketplace_service import (
    TechnicianServiceOfferService,
    TechnicianServiceRequestService,
)


class ScopedPublicApiSerializerMixin:
    def get_scope_request(self):
        return self.context.get("request")


class PublicCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("public_id", "name", "slug", "status")


class PublicSiteSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="maintenance_client.company.name", read_only=True)

    class Meta:
        model = OperationalSite
        fields = ("public_id", "name", "code", "city", "state", "company")


class PublicContextSerializer(serializers.Serializer):
    user = serializers.DictField()
    authentication_mode = serializers.CharField()
    active_company = PublicCompanySerializer(allow_null=True)
    active_site = PublicSiteSerializer(allow_null=True)
    companies = PublicCompanySerializer(many=True)
    sites = PublicSiteSerializer(many=True)
    permissions = serializers.ListField(child=serializers.CharField())
    billing = serializers.DictField()


class PublicAssetCategorySerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class PublicAssetSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    site = PublicSiteSerializer(source="operational_site", read_only=True)
    category = PublicAssetCategorySerializer(read_only=True)
    operational_site_id = serializers.SlugRelatedField(
        source="operational_site",
        slug_field="public_id",
        queryset=OperationalSite.objects.all(),
        write_only=True,
        required=False,
    )
    category_id = serializers.SlugRelatedField(
        source="category",
        slug_field="public_id",
        queryset=ChecklistItem.objects.none(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Asset
        fields = (
            "public_id",
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
            "site",
            "category",
            "operational_site_id",
            "category_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.smart_system.models import AssetCategory
        from apps.public_api.services.scoping import PublicApiScopeService

        request = self.get_scope_request()
        self.fields["category_id"].queryset = AssetCategory.objects.all()
        if request is not None:
            self.fields["operational_site_id"].queryset = PublicApiScopeService.scope_queryset(
                OperationalSite.objects.all(),
                request,
            )


class PublicMaintenancePlanSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="company.name", read_only=True)
    site = serializers.CharField(source="operational_site.name", read_only=True)
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    checklist_name = serializers.CharField(source="checklist.name", read_only=True)

    class Meta:
        model = MaintenancePlan
        fields = (
            "public_id",
            "name",
            "description",
            "frequency_type",
            "frequency_value",
            "estimated_duration_minutes",
            "is_active",
            "notes",
            "next_due_date",
            "company",
            "site",
            "asset_tag",
            "checklist_name",
            "created_at",
            "updated_at",
        )


class PublicServiceOrderSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.display_name", read_only=True)
    site_name = serializers.CharField(source="operational_site.name", read_only=True)
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    client_id = serializers.SlugRelatedField(source="client", slug_field="public_id", queryset=Company.objects.none(), write_only=True, required=False)
    operational_site_id = serializers.SlugRelatedField(source="operational_site", slug_field="public_id", queryset=OperationalSite.objects.all(), write_only=True, required=False)
    asset_id = serializers.SlugRelatedField(source="asset", slug_field="public_id", queryset=Asset.objects.all(), write_only=True, required=False, allow_null=True)
    maintenance_plan_id = serializers.SlugRelatedField(source="maintenance_plan", slug_field="public_id", queryset=MaintenancePlan.objects.all(), write_only=True, required=False, allow_null=True)
    assigned_to_id = serializers.SlugRelatedField(source="assigned_to", slug_field="public_id", queryset=Company.objects.none(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = ServiceOrder
        fields = (
            "public_id",
            "order_number",
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
            "final_observations",
            "notes",
            "client_name",
            "site_name",
            "asset_tag",
            "client_id",
            "operational_site_id",
            "asset_id",
            "maintenance_plan_id",
            "assigned_to_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "order_number", "opened_at", "started_at", "completed_at", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.smart_system.models import MaintenanceClient
        from apps.public_api.services.scoping import PublicApiScopeService
        from apps.users.models import User

        request = self.get_scope_request()
        self.fields["client_id"].queryset = MaintenanceClient.objects.none()
        self.fields["assigned_to_id"].queryset = User.objects.none()
        if request is not None:
            self.fields["client_id"].queryset = PublicApiScopeService.scope_queryset(
                MaintenanceClient.objects.all(),
                request,
            )
            self.fields["operational_site_id"].queryset = PublicApiScopeService.scope_queryset(
                OperationalSite.objects.all(),
                request,
            )
            self.fields["asset_id"].queryset = PublicApiScopeService.scope_queryset(
                Asset.objects.all(),
                request,
            )
            self.fields["maintenance_plan_id"].queryset = PublicApiScopeService.scope_queryset(
                MaintenancePlan.objects.all(),
                request,
            )
            scope = PublicApiScopeService.resolve_scope(request)
            if scope.company is not None:
                self.fields["assigned_to_id"].queryset = User.objects.filter(
                    memberships__company=scope.company,
                    memberships__status="active",
                    is_active=True,
                ).distinct()


class PublicFailureSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    order_number = serializers.CharField(source="service_order.order_number", read_only=True)
    asset_id = serializers.SlugRelatedField(source="asset", slug_field="public_id", queryset=Asset.objects.all(), write_only=True, required=False)
    service_order_id = serializers.SlugRelatedField(source="service_order", slug_field="public_id", queryset=ServiceOrder.objects.all(), write_only=True, allow_null=True, required=False)

    class Meta:
        model = FailureEvent
        fields = (
            "public_id",
            "detected_at",
            "symptom",
            "probable_cause",
            "root_cause",
            "severity",
            "downtime_minutes",
            "status",
            "notes",
            "asset_tag",
            "order_number",
            "asset_id",
            "service_order_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.public_api.services.scoping import PublicApiScopeService

        request = self.get_scope_request()
        if request is not None:
            self.fields["asset_id"].queryset = PublicApiScopeService.scope_queryset(Asset.objects.all(), request)
            self.fields["service_order_id"].queryset = PublicApiScopeService.scope_queryset(ServiceOrder.objects.all(), request)


class PublicChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ("public_id", "title", "description", "item_type", "ordering", "is_required")


class PublicChecklistSerializer(serializers.ModelSerializer):
    items = PublicChecklistItemSerializer(many=True, read_only=True)
    company = serializers.CharField(source="company.name", read_only=True)
    site = serializers.CharField(source="operational_site.name", read_only=True)

    class Meta:
        model = Checklist
        fields = ("public_id", "name", "description", "is_active", "company", "site", "items", "created_at", "updated_at")


class PublicChecklistExecutionSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    service_order_number = serializers.CharField(source="service_order.order_number", read_only=True)
    checklist_item_title = serializers.CharField(source="checklist_item.title", read_only=True)
    service_order_id = serializers.SlugRelatedField(source="service_order", slug_field="public_id", queryset=ServiceOrder.objects.all())
    checklist_item_id = serializers.SlugRelatedField(source="checklist_item", slug_field="public_id", queryset=ChecklistItem.objects.all())

    class Meta:
        model = ServiceOrderChecklistResponse
        fields = (
            "public_id",
            "service_order_number",
            "checklist_item_title",
            "service_order_id",
            "checklist_item_id",
            "response_boolean",
            "response_text",
            "response_number",
            "response_choice",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.public_api.services.scoping import PublicApiScopeService

        request = self.get_scope_request()
        if request is not None:
            self.fields["service_order_id"].queryset = PublicApiScopeService.scope_queryset(ServiceOrder.objects.all(), request)
            self.fields["checklist_item_id"].queryset = PublicApiScopeService.scope_queryset(ChecklistItem.objects.all(), request)


class PublicPartSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="company.name", read_only=True)
    site = serializers.CharField(source="operational_site.name", read_only=True)
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Part
        fields = (
            "public_id",
            "code",
            "name",
            "description",
            "manufacturer",
            "model",
            "category",
            "unit",
            "unit_cost",
            "current_stock",
            "minimum_stock",
            "maximum_stock",
            "location",
            "primary_supplier",
            "status",
            "company",
            "site",
            "low_stock",
            "created_at",
            "updated_at",
        )

    def get_low_stock(self, obj):
        return obj.current_stock <= obj.minimum_stock


class PublicStockMovementSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    service_order_number = serializers.CharField(source="service_order.order_number", read_only=True)
    performed_by_email = serializers.CharField(source="performed_by.email", read_only=True)
    part_id = serializers.SlugRelatedField(source="part", slug_field="public_id", queryset=Part.objects.all(), write_only=True)
    service_order_id = serializers.SlugRelatedField(source="service_order", slug_field="public_id", queryset=ServiceOrder.objects.all(), write_only=True, allow_null=True, required=False)

    class Meta:
        model = StockMovement
        fields = (
            "public_id",
            "movement_type",
            "quantity",
            "reference_type",
            "reference_id",
            "notes",
            "occurred_at",
            "part_code",
            "service_order_number",
            "performed_by_email",
            "part_id",
            "service_order_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.public_api.services.scoping import PublicApiScopeService

        request = self.get_scope_request()
        if request is not None:
            self.fields["part_id"].queryset = PublicApiScopeService.scope_queryset(Part.objects.all(), request)
            self.fields["service_order_id"].queryset = PublicApiScopeService.scope_queryset(ServiceOrder.objects.all(), request)


class PublicPartAssetLinkSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)

    class Meta:
        model = PartAssetLink
        fields = ("public_id", "part_code", "asset_tag", "quantity_recommended", "notes")


class PublicReportMetadataSerializer(serializers.Serializer):
    report_type = serializers.CharField()
    document_type = serializers.CharField()
    reference_code = serializers.CharField()
    reference_label = serializers.CharField()
    company = serializers.CharField(allow_blank=True)
    site = serializers.CharField(allow_blank=True)
    download_url = serializers.CharField(required=False, allow_blank=True)


class PublicTechnicianProfileSerializer(serializers.ModelSerializer):
    specialties = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = (
            "public_id",
            "display_name",
            "company_name",
            "certifications",
            "profile_type",
            "experience_years",
            "service_radius_km",
            "verification_status",
            "marketplace_status",
            "rating_average",
            "completed_jobs_count",
            "is_active",
            "specialties",
            "created_at",
            "updated_at",
        )

    def get_specialties(self, obj):
        return [assignment.skill.name for assignment in obj.skill_assignments.select_related("skill").all()]


class PublicMarketplaceServiceRequestSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    company_name = serializers.CharField(source="requester_company.name", read_only=True)
    site_name = serializers.CharField(source="related_site.name", read_only=True)
    asset_tag = serializers.CharField(source="related_asset.asset_tag", read_only=True)
    offers_count = serializers.IntegerField(read_only=True)
    requester_company_id = serializers.SlugRelatedField(
        source="requester_company",
        slug_field="public_id",
        queryset=Company.objects.none(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    related_site_id = serializers.SlugRelatedField(
        source="related_site",
        slug_field="public_id",
        queryset=OperationalSite.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    related_asset_id = serializers.SlugRelatedField(
        source="related_asset",
        slug_field="public_id",
        queryset=Asset.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    related_service_order_id = serializers.SlugRelatedField(
        source="related_service_order",
        slug_field="public_id",
        queryset=ServiceOrder.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = TechnicianServiceRequest
        fields = (
            "public_id",
            "title",
            "description",
            "category",
            "service_type",
            "priority",
            "requested_date",
            "deadline_at",
            "city",
            "state",
            "address_line",
            "location_label",
            "status",
            "origin",
            "notes",
            "company_name",
            "site_name",
            "asset_tag",
            "offers_count",
            "requester_company_id",
            "related_site_id",
            "related_asset_id",
            "related_service_order_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "status", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.public_api.services.scoping import PublicApiScopeService

        request = self.get_scope_request()
        if request is not None:
            scope = PublicApiScopeService.resolve_scope(request)
            self.fields["requester_company_id"].queryset = Company.objects.filter(id__in=[company.id for company in scope.companies])
            self.fields["related_site_id"].queryset = PublicApiScopeService.scope_queryset(OperationalSite.objects.all(), request)
            self.fields["related_asset_id"].queryset = PublicApiScopeService.scope_queryset(Asset.objects.all(), request)
            self.fields["related_service_order_id"].queryset = PublicApiScopeService.scope_queryset(ServiceOrder.objects.all(), request)

    def create(self, validated_data):
        request = self.get_scope_request()
        return TechnicianServiceRequestService.create_request(
            user=request.user,
            validated_data=validated_data,
        )


class PublicMarketplaceOfferSerializer(ScopedPublicApiSerializerMixin, serializers.ModelSerializer):
    request_title = serializers.CharField(source="service_request.title", read_only=True)
    technician_name = serializers.CharField(source="technician_profile.display_name", read_only=True)
    service_request_id = serializers.SlugRelatedField(
        source="service_request",
        slug_field="public_id",
        queryset=TechnicianServiceRequest.objects.all(),
    )
    technician_profile_id = serializers.SlugRelatedField(
        source="technician_profile",
        slug_field="public_id",
        queryset=TechnicianProfile.objects.all(),
    )

    class Meta:
        model = TechnicianServiceOffer
        fields = (
            "public_id",
            "request_title",
            "technician_name",
            "service_request_id",
            "technician_profile_id",
            "proposed_amount",
            "message",
            "estimated_hours",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "status", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.marketplace_technicians.services.access import MarketplaceAccessService

        request = self.get_scope_request()
        if request is not None:
            self.fields["service_request_id"].queryset = MarketplaceAccessService.scope_requests_queryset(
                request.user,
                TechnicianServiceRequest.objects.all(),
            )
            self.fields["technician_profile_id"].queryset = MarketplaceAccessService.scope_profiles_queryset(
                request.user,
                TechnicianProfile.objects.all(),
            )

    def create(self, validated_data):
        request = self.get_scope_request()
        return TechnicianServiceOfferService.create_offer(
            user=request.user,
            validated_data=validated_data,
        )


class PublicMarketplaceAssignmentSerializer(serializers.ModelSerializer):
    request_public_id = serializers.UUIDField(source="technician_service_request.public_id", read_only=True)
    request_title = serializers.CharField(source="technician_service_request.title", read_only=True)
    technician_name = serializers.CharField(source="technician_profile.display_name", read_only=True)
    service_order_number = serializers.CharField(source="technician_service_request.related_service_order.order_number", read_only=True)

    class Meta:
        model = TechnicianAssignment
        fields = (
            "public_id",
            "request_public_id",
            "request_title",
            "technician_name",
            "service_order_number",
            "assignment_status",
            "assigned_at",
            "started_at",
            "completed_at",
            "notes",
            "created_at",
            "updated_at",
        )


class PublicMarketplaceReviewSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source="technician_profile.display_name", read_only=True)
    assignment_public_id = serializers.UUIDField(source="assignment.public_id", read_only=True)

    class Meta:
        model = TechnicianReview
        fields = (
            "public_id",
            "technician_name",
            "assignment_public_id",
            "rating",
            "comment",
            "status",
            "created_at",
            "updated_at",
        )


class PublicMarketplaceMatchSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source="technician_profile.display_name", read_only=True)
    request_public_id = serializers.UUIDField(source="technician_service_request.public_id", read_only=True)
    request_title = serializers.CharField(source="technician_service_request.title", read_only=True)

    class Meta:
        model = TechnicianMatchingRecord
        fields = (
            "public_id",
            "request_public_id",
            "request_title",
            "technician_name",
            "ranking_position",
            "match_score",
            "score_specialty",
            "score_distance",
            "score_rating",
            "score_experience",
            "score_availability",
            "score_response_time",
            "distance_km",
            "match_reason",
            "status",
            "updated_at",
        )
