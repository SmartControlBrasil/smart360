from rest_framework import serializers

from apps.companies.models import Company

from ..models import (
    ConfiguratorOption,
    ConfiguratorQuestion,
    DeliveryRecord,
    Niche,
    ProductionTask,
    SiteOrder,
    SiteOrderAnswer,
    SiteProjectIntake,
    Template,
    TemplateRecommendationRule,
)
from ..services.order_service import DeliveryService, SiteOrderService


class NicheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niche
        fields = ("public_id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class TemplateSerializer(serializers.ModelSerializer):
    niche_id = serializers.UUIDField(source="niche.public_id", read_only=True)
    niche_name = serializers.CharField(source="niche.name", read_only=True)

    class Meta:
        model = Template
        fields = (
            "public_id",
            "niche",
            "niche_id",
            "niche_name",
            "name",
            "slug",
            "description",
            "version",
            "template_type",
            "base_price",
            "status",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ConfiguratorOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguratorOption
        fields = ("public_id", "question", "label", "value", "order", "is_active", "metadata", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class ConfiguratorQuestionSerializer(serializers.ModelSerializer):
    options = ConfiguratorOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ConfiguratorQuestion
        fields = (
            "public_id",
            "niche",
            "text",
            "question_type",
            "order",
            "is_active",
            "metadata",
            "options",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class TemplateRecommendationRuleSerializer(serializers.ModelSerializer):
    niche_name = serializers.CharField(source="niche.name", read_only=True)
    template_name = serializers.CharField(source="recommended_template.name", read_only=True)

    class Meta:
        model = TemplateRecommendationRule
        fields = (
            "public_id",
            "niche",
            "niche_name",
            "question",
            "option",
            "recommended_template",
            "template_name",
            "priority",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class SiteOrderAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)
    option_label = serializers.CharField(source="option.label", read_only=True)

    class Meta:
        model = SiteOrderAnswer
        fields = (
            "public_id",
            "question",
            "question_text",
            "option",
            "option_label",
            "value_text",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class SiteOrderAnswerInputSerializer(serializers.Serializer):
    question = serializers.PrimaryKeyRelatedField(queryset=ConfiguratorQuestion.objects.all())
    option = serializers.PrimaryKeyRelatedField(queryset=ConfiguratorOption.objects.all(), required=False, allow_null=True)
    value_text = serializers.CharField(required=False, allow_blank=True)


class SiteOrderSerializer(serializers.ModelSerializer):
    answers = SiteOrderAnswerSerializer(many=True, read_only=True)
    company_id = serializers.UUIDField(source="company.public_id", read_only=True)
    requester_id = serializers.UUIDField(source="requester.public_id", read_only=True)
    selected_template_slug = serializers.CharField(source="selected_template.slug", read_only=True)
    recommended_template_slug = serializers.CharField(source="recommended_template.slug", read_only=True)

    class Meta:
        model = SiteOrder
        fields = (
            "public_id",
            "company",
            "company_id",
            "requester",
            "requester_id",
            "niche",
            "selected_template",
            "selected_template_slug",
            "recommended_template",
            "recommended_template_slug",
            "status",
            "notes",
            "final_price",
            "ordered_at",
            "production_started_at",
            "delivered_at",
            "metadata",
            "answers",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "public_id",
            "requester",
            "recommended_template",
            "ordered_at",
            "production_started_at",
            "delivered_at",
            "created_at",
            "updated_at",
        )


class SiteOrderCreateSerializer(serializers.ModelSerializer):
    answers = SiteOrderAnswerInputSerializer(many=True, required=False)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False, allow_null=True)
    selected_template = serializers.PrimaryKeyRelatedField(queryset=Template.objects.filter(is_active=True), required=False, allow_null=True)

    class Meta:
        model = SiteOrder
        fields = ("company", "niche", "selected_template", "status", "notes", "final_price", "metadata", "answers")

    def create(self, validated_data):
        return SiteOrderService.create_order(requester=self.context["request"].user, validated_data=validated_data)


class SiteProjectIntakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteProjectIntake
        fields = (
            "public_id",
            "site_order",
            "company_name",
            "phone",
            "whatsapp",
            "address",
            "city",
            "state",
            "business_description",
            "main_services",
            "instagram",
            "facebook",
            "logo_url",
            "photo_gallery",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ProductionTaskSerializer(serializers.ModelSerializer):
    assignee_email = serializers.CharField(source="assignee.email", read_only=True)

    class Meta:
        model = ProductionTask
        fields = (
            "public_id",
            "site_order",
            "stage",
            "status",
            "assignee",
            "assignee_email",
            "due_date",
            "notes",
            "order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class DeliveryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryRecord
        fields = (
            "public_id",
            "site_order",
            "delivered_url",
            "delivered_at",
            "acceptance_status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        record = super().create(validated_data)
        DeliveryService.register_delivery(record=record)
        return record
