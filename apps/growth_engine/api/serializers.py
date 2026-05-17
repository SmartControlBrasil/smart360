from rest_framework import serializers

from apps.users.models import User

from ..models import Lead, LeadAssignment, LeadCampaign, LeadInteraction, LeadQualification, LeadSource, LeadTag
from ..services.lead_service import LeadScoringService, LeadService


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = ("public_id", "name", "source_type", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class LeadTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTag
        fields = ("public_id", "name", "slug", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class LeadCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadCampaign
        fields = ("public_id", "name", "objective", "channel", "status", "description", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class LeadInteractionSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = LeadInteraction
        fields = (
            "public_id",
            "lead",
            "interaction_type",
            "channel",
            "summary",
            "happened_at",
            "owner",
            "owner_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class LeadAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = LeadAssignment
        fields = ("public_id", "lead", "user", "user_email", "status", "assigned_at", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class LeadQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadQualification
        fields = ("public_id", "lead", "criteria", "calculated_score", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "calculated_score", "created_at", "updated_at")

    def create(self, validated_data):
        qualification = super().create(validated_data)
        lead = qualification.lead
        qualification.calculated_score = LeadScoringService.calculate_score(lead=lead, qualification_criteria=qualification.criteria)
        qualification.save(update_fields=["calculated_score", "updated_at"])
        lead.score = qualification.calculated_score
        lead.save(update_fields=["score", "updated_at"])
        return qualification

    def update(self, instance, validated_data):
        qualification = super().update(instance, validated_data)
        lead = qualification.lead
        qualification.calculated_score = LeadScoringService.calculate_score(lead=lead, qualification_criteria=qualification.criteria)
        qualification.save(update_fields=["calculated_score", "updated_at"])
        lead.score = qualification.calculated_score
        lead.save(update_fields=["score", "updated_at"])
        return qualification


class LeadSerializer(serializers.ModelSerializer):
    tags = LeadTagSerializer(many=True, read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    niche_name = serializers.CharField(source="niche.name", read_only=True)
    assigned_to_email = serializers.CharField(source="assigned_to.email", read_only=True)

    class Meta:
        model = Lead
        fields = (
            "public_id",
            "company_name",
            "contact_name",
            "email",
            "phone",
            "whatsapp",
            "website",
            "city",
            "state",
            "niche",
            "niche_name",
            "source",
            "source_name",
            "campaign",
            "status",
            "score",
            "notes",
            "assigned_to",
            "assigned_to_email",
            "created_by",
            "tags",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "score", "created_by", "created_at", "updated_at")


class LeadWriteSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(queryset=LeadTag.objects.all(), many=True, required=False, write_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Lead
        fields = (
            "company_name",
            "contact_name",
            "email",
            "phone",
            "whatsapp",
            "website",
            "city",
            "state",
            "niche",
            "source",
            "campaign",
            "status",
            "notes",
            "assigned_to",
            "metadata",
            "tag_ids",
        )

    def create(self, validated_data):
        return LeadService.create_lead(user=self.context["request"].user, validated_data=validated_data)

    def update(self, instance, validated_data):
        return LeadService.update_lead(lead=instance, validated_data=validated_data, user=self.context["request"].user)
