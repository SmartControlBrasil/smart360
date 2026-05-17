from rest_framework import serializers

from ..models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianAvailability,
    TechnicianCompensationRecord,
    TechnicianMatchingRecord,
    TechnicianPortfolioItem,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
    TechnicianWorkReport,
)
from ..services.marketplace_service import (
    CompensationService,
    TechnicianAssignmentService,
    TechnicianMatchingService,
    TechnicianReviewService,
    TechnicianServiceOfferService,
    TechnicianServiceRequestService,
    TechnicianWorkReportService,
)


class TechnicianProfileSerializer(serializers.ModelSerializer):
    specialties = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = (
            "public_id",
            "user",
            "company",
            "display_name",
            "document_number",
            "phone",
            "whatsapp",
            "email",
            "bio",
            "certifications",
            "profile_type",
            "experience_years",
            "service_radius_km",
            "verification_status",
            "marketplace_status",
            "trust_case_reference",
            "rating_average",
            "completed_jobs_count",
            "is_active",
            "notes",
            "metadata",
            "specialties",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "rating_average", "completed_jobs_count", "created_at", "updated_at")

    def get_specialties(self, obj):
        return list(obj.skill_assignments.select_related("skill").values_list("skill__name", flat=True))


class TechnicianSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianSkill
        fields = ("public_id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class TechnicianSkillAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianSkillAssignment
        fields = (
            "public_id",
            "technician_profile",
            "skill",
            "proficiency_level",
            "years_experience",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ServiceRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRegion
        fields = ("public_id", "name", "state", "city", "region_type", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianServiceRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianServiceRegion
        fields = ("public_id", "technician_profile", "service_region", "coverage_type", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianAvailability
        fields = ("public_id", "technician_profile", "weekday", "start_time", "end_time", "is_available", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianPortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianPortfolioItem
        fields = ("public_id", "technician_profile", "title", "description", "media_file", "media_url", "is_active", "ordering", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class TechnicianServiceRequestSerializer(serializers.ModelSerializer):
    offers_count = serializers.SerializerMethodField()
    assignment_public_id = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianServiceRequest
        fields = (
            "public_id",
            "requester_user",
            "requester_company",
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
            "related_client",
            "related_site",
            "related_asset",
            "related_service_order",
            "notes",
            "offers_count",
            "assignment_public_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def get_offers_count(self, obj):
        return obj.offers.count()

    def get_assignment_public_id(self, obj):
        assignment = obj.assignments.order_by("-assigned_at").first()
        return str(assignment.public_id) if assignment else None

    def create(self, validated_data):
        return TechnicianServiceRequestService.create_request(
            user=self.context["request"].user,
            validated_data=validated_data,
        )


class TechnicianServiceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianServiceOffer
        fields = (
            "public_id",
            "service_request",
            "technician_profile",
            "proposed_amount",
            "message",
            "estimated_hours",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "status", "created_at", "updated_at")

    def create(self, validated_data):
        return TechnicianServiceOfferService.create_offer(
            user=self.context["request"].user,
            validated_data=validated_data,
        )


class TechnicianMatchingRecordSerializer(serializers.ModelSerializer):
    technician_display_name = serializers.CharField(source="technician_profile.display_name", read_only=True)

    class Meta:
        model = TechnicianMatchingRecord
        fields = (
            "public_id",
            "technician_service_request",
            "technician_profile",
            "technician_display_name",
            "match_score",
            "score_specialty",
            "score_distance",
            "score_rating",
            "score_experience",
            "score_availability",
            "score_response_time",
            "distance_km",
            "ranking_position",
            "scoring_version",
            "match_reason",
            "calculation_context",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        if not validated_data.get("match_score"):
            validated_data["match_score"] = TechnicianMatchingService.calculate_match_score(
                technician_profile=validated_data["technician_profile"],
                service_request=validated_data["technician_service_request"],
            )
        return super().create(validated_data)


class TechnicianAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianAssignment
        fields = (
            "public_id",
            "technician_service_request",
            "technician_profile",
            "service_offer",
            "assignment_status",
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
        return TechnicianAssignmentService.assign(
            service_request=validated_data["technician_service_request"],
            technician_profile=validated_data["technician_profile"],
            notes=validated_data.get("notes", ""),
        )


class TechnicianWorkReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianWorkReport
        fields = (
            "public_id",
            "technician_assignment",
            "summary",
            "execution_notes",
            "started_at",
            "ended_at",
            "labor_minutes",
            "materials_used",
            "next_recommendation",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "labor_minutes", "created_at", "updated_at")

    def create(self, validated_data):
        report = super().create(validated_data)
        return TechnicianWorkReportService.sync_labor_minutes(work_report=report)

    def update(self, instance, validated_data):
        report = super().update(instance, validated_data)
        return TechnicianWorkReportService.sync_labor_minutes(work_report=report)


class TechnicianReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianReview
        fields = (
            "public_id",
            "technician_profile",
            "assignment",
            "reviewer_user",
            "reviewer_company",
            "rating",
            "comment",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        assignment = validated_data["assignment"]
        validated_data["technician_profile"] = assignment.technician_profile
        return TechnicianReviewService.create_review(user=self.context["request"].user, validated_data=validated_data)


class TechnicianCompensationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianCompensationRecord
        fields = (
            "public_id",
            "technician_assignment",
            "gross_amount",
            "platform_fee",
            "net_amount",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def validate(self, attrs):
        return CompensationService.create_or_update(validated_data=attrs)
