from rest_framework import serializers

from ..models import (
    AnalyticalAssignment,
    AnalyticalMatchingRecord,
    AnalyticalProvider,
    AnalyticalReport,
    AnalyticalRequest,
    AnalyticalReview,
    AnalyticalService,
    AnalyticalServiceCapability,
    AnalyticalServiceCategory,
    AnalyticalServiceRegion,
)
from ..services.analytical_service import (
    AnalyticalAssignmentService,
    AnalyticalMatchingService,
    AnalyticalReviewService,
)


class AnalyticalProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalProvider
        fields = (
            "public_id",
            "company",
            "user",
            "display_name",
            "legal_name",
            "document_number",
            "contact_email",
            "contact_phone",
            "website",
            "description",
            "provider_type",
            "verification_status",
            "marketplace_status",
            "trust_case_reference",
            "knowledge_profile_reference",
            "rating_average",
            "completed_jobs_count",
            "is_active",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "rating_average", "completed_jobs_count", "created_at", "updated_at")


class AnalyticalServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalServiceCategory
        fields = ("public_id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class AnalyticalServiceCapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalServiceCapability
        fields = ("public_id", "analytical_service", "capability_name", "description", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticalServiceRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalServiceRegion
        fields = ("public_id", "analytical_service", "region_name", "state", "country", "coverage_type", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticalServiceSerializer(serializers.ModelSerializer):
    capabilities = AnalyticalServiceCapabilitySerializer(many=True, read_only=True)
    service_regions = AnalyticalServiceRegionSerializer(many=True, read_only=True)

    class Meta:
        model = AnalyticalService
        fields = (
            "public_id",
            "provider",
            "category",
            "title",
            "description",
            "service_type",
            "delivery_type",
            "estimated_turnaround_days",
            "price_model",
            "base_price",
            "currency",
            "is_active",
            "notes",
            "capabilities",
            "service_regions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalRequest
        fields = (
            "public_id",
            "requester_user",
            "requester_company",
            "title",
            "description",
            "category",
            "priority",
            "related_asset",
            "related_site",
            "related_service_order",
            "city",
            "state",
            "country",
            "requested_date",
            "status",
            "origin",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticalMatchingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalMatchingRecord
        fields = (
            "public_id",
            "analytical_request",
            "provider",
            "match_score",
            "match_reason",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        if not validated_data.get("match_score"):
            validated_data["match_score"] = AnalyticalMatchingService.calculate_match_score(
                provider=validated_data["provider"],
                analytical_request=validated_data["analytical_request"],
            )
        return super().create(validated_data)


class AnalyticalAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalAssignment
        fields = (
            "public_id",
            "analytical_request",
            "provider",
            "status",
            "assigned_at",
            "accepted_at",
            "declined_at",
            "started_at",
            "completed_at",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "public_id",
            "assigned_at",
            "accepted_at",
            "declined_at",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        return AnalyticalAssignmentService.assign(
            analytical_request=validated_data["analytical_request"],
            provider=validated_data["provider"],
            notes=validated_data.get("notes", ""),
        )


class AnalyticalReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalReport
        fields = (
            "public_id",
            "analytical_assignment",
            "title",
            "summary",
            "report_file",
            "technical_conclusion",
            "recommendations",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticalReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalReview
        fields = (
            "public_id",
            "analytical_assignment",
            "reviewer_user",
            "reviewer_company",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return AnalyticalReviewService.create_review(user=self.context["request"].user, validated_data=validated_data)
