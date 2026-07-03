from rest_framework import serializers

from apps.companies.models import Company
from apps.smart_system.models import OperationalSite
from apps.ai_agents_center.models import (
    AIBriefing,
    AIBriefingDelivery,
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentDefinition,
    AgentExecutionPolicy,
    AgentMarketplaceRequestFlag,
    AgentMemoryEntry,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
    CommercialOpportunity,
    AtlasProspectImportBatch,
    ManagerCopilotConfiguration,
    ManagerCopilotMessage,
    ManagerCopilotSession,
)


class AgentExecutionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentExecutionPolicy
        fields = (
            "public_id",
            "require_human_approval",
            "allow_manual_runs",
            "allow_scheduled_runs",
            "enforce_billing_active",
            "allowed_tools",
            "allowed_action_types",
            "max_recommendations",
            "is_active",
            "config",
        )


class AIBriefingDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIBriefingDelivery
        fields = (
            "public_id",
            "channel",
            "status",
            "delivered_at",
            "viewed_at",
            "metadata",
        )


class AIBriefingSerializer(serializers.ModelSerializer):
    deliveries = AIBriefingDeliverySerializer(many=True, read_only=True)

    class Meta:
        model = AIBriefing
        fields = (
            "public_id",
            "briefing_type",
            "audience",
            "title",
            "summary",
            "period_label",
            "period_start",
            "period_end",
            "content",
            "source_agents",
            "source_recommendation_ids",
            "source_proposal_ids",
            "filters",
            "status",
            "generated_at",
            "delivered_at",
            "viewed_at",
            "deliveries",
        )


class AIBriefingGenerateSerializer(serializers.Serializer):
    briefing_type = serializers.ChoiceField(choices=AIBriefing.BriefingType.choices)
    audience = serializers.ChoiceField(choices=AIBriefing.Audience.choices)
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    site = serializers.PrimaryKeyRelatedField(read_only=True)
    user_id = serializers.IntegerField(required=False)
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)


class AgentDefinitionSerializer(serializers.ModelSerializer):
    execution_policy = AgentExecutionPolicySerializer(read_only=True)

    class Meta:
        model = AgentDefinition
        fields = (
            "public_id",
            "slug",
            "name",
            "description",
            "domain",
            "status",
            "autonomy_level",
            "enabled",
            "config",
            "execution_policy",
            "created_at",
            "updated_at",
        )


class AgentRunSerializer(serializers.ModelSerializer):
    agent = AgentDefinitionSerializer(read_only=True)

    class Meta:
        model = AgentRun
        fields = (
            "public_id",
            "agent",
            "trigger_type",
            "trigger_reference",
            "status",
            "input_context",
            "output_summary",
            "request_id",
            "correlation_id",
            "started_at",
            "finished_at",
            "duration_ms",
            "error_message",
            "created_at",
            "updated_at",
        )


class AgentRecommendationSerializer(serializers.ModelSerializer):
    agent_run = AgentRunSerializer(read_only=True)

    class Meta:
        model = AgentRecommendation
        fields = (
            "public_id",
            "agent_run",
            "recommendation_type",
            "title",
            "summary",
            "explanation",
            "evidence_summary",
            "suggested_action",
            "payload",
            "severity",
            "priority",
            "status",
            "attention_score",
            "requires_human_approval",
            "entity_type",
            "entity_id",
            "created_at",
            "updated_at",
        )


class AgentActionProposalSerializer(serializers.ModelSerializer):
    agent_run = AgentRunSerializer(read_only=True)

    class Meta:
        model = AgentActionProposal
        fields = (
            "public_id",
            "agent_run",
            "action_type",
            "target_entity",
            "target_entity_id",
            "title",
            "summary",
            "proposed_payload",
            "priority",
            "approval_required",
            "status",
            "approved_at",
            "rejected_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )


class CommercialOpportunitySerializer(serializers.ModelSerializer):
    lead_public_id = serializers.UUIDField(source="lead.public_id", read_only=True)

    class Meta:
        model = CommercialOpportunity
        fields = (
            "public_id",
            "title",
            "company_name",
            "segment",
            "city",
            "state",
            "source",
            "problem_detected",
            "opportunity_description",
            "recommended_solution",
            "recommended_product",
            "confidence_score",
            "commercial_score",
            "status",
            "metadata",
            "outreach_channel",
            "outreach_sender_email",
            "outreach_domain",
            "outreach_status",
            "outreach_notes",
            "lead_public_id",
            "created_at",
            "updated_at",
        )


class AtlasProspectRowSerializer(serializers.Serializer):
    company_name = serializers.CharField(required=False, allow_blank=True)
    segment = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)
    contact_name = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(required=False, allow_blank=True)


class AtlasProspectImportSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.companies.models import Company

        self.fields["company"] = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())

    source = serializers.ChoiceField(
        choices=CommercialOpportunity.Source.choices,
        default=CommercialOpportunity.Source.MANUAL,
        required=False,
    )
    filename = serializers.CharField(required=False, allow_blank=True, default="")
    rows = AtlasProspectRowSerializer(many=True)


class AtlasProspectImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasProspectImportBatch
        fields = (
            "public_id",
            "source",
            "filename",
            "total_rows",
            "processed_rows",
            "created_opportunities",
            "skipped_duplicates",
            "skipped_empty_rows",
            "errors",
            "status",
            "created_at",
            "updated_at",
        )


class AgentMemoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMemoryEntry
        fields = (
            "public_id",
            "entity_type",
            "entity_id",
            "memory_kind",
            "content",
            "metadata",
            "created_at",
            "updated_at",
        )


class AgentManualRunSerializer(serializers.Serializer):
    agent_slug = serializers.SlugField()
    company = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Company.objects.all())
    site = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=OperationalSite.objects.all())
    trigger_reference = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        from apps.companies.models import Membership

        request = self.context.get("request")
        user = getattr(request, "user", None)
        company = attrs.get("company")
        site = attrs.get("site")

        if user is not None and not getattr(user, "is_superuser", False):
            memberships = Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            if company is None:
                primary_membership = memberships.filter(is_primary=True).select_related("company").first()
                company = primary_membership.company if primary_membership else None
                attrs["company"] = company
            elif not memberships.filter(company=company).exists():
                raise serializers.ValidationError({"company": "Usuario sem acesso a esta empresa."})

        if site is not None and company is not None and site.maintenance_client.company_id != company.id:
            raise serializers.ValidationError({"site": "Unidade fora do escopo da empresa informada."})
        return attrs


class AgentAssetAttentionFlagSerializer(serializers.ModelSerializer):
    latest_recommendation = AgentRecommendationSerializer(read_only=True)
    asset = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()

    class Meta:
        model = AgentAssetAttentionFlag
        fields = (
            "public_id",
            "asset",
            "site",
            "status",
            "attention_score",
            "summary",
            "risk_level",
            "payload",
            "last_detected_at",
            "created_at",
            "updated_at",
            "latest_recommendation",
        )

    def get_asset(self, obj):
        return {
            "public_id": str(obj.asset.public_id),
            "asset_tag": obj.asset.asset_tag,
            "name": obj.asset.name,
            "criticality": obj.asset.criticality,
            "category": obj.asset.category.name,
        }

    def get_site(self, obj):
        if obj.site is None:
            return None
        return {
            "public_id": str(obj.site.public_id),
            "name": obj.site.name,
            "code": obj.site.code,
        }


class ProposalDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class AgentScheduleHealthFlagSerializer(serializers.ModelSerializer):
    latest_recommendation = AgentRecommendationSerializer(read_only=True)
    technician = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()

    class Meta:
        model = AgentScheduleHealthFlag
        fields = (
            "public_id",
            "flag_type",
            "technician",
            "site",
            "schedule_date",
            "status",
            "attention_score",
            "summary",
            "risk_level",
            "payload",
            "last_detected_at",
            "created_at",
            "updated_at",
            "latest_recommendation",
        )

    def get_technician(self, obj):
        if obj.technician is None:
            return None
        return {
            "id": obj.technician_id,
            "name": obj.technician.display_name or obj.technician.email,
            "email": obj.technician.email,
        }

    def get_site(self, obj):
        if obj.site is None:
            return None
        return {
            "public_id": str(obj.site.public_id),
            "name": obj.site.name,
            "code": obj.site.code,
        }


class AgentProfitabilityAttentionFlagSerializer(serializers.ModelSerializer):
    latest_recommendation = AgentRecommendationSerializer(read_only=True)
    target = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfitabilityAttentionFlag
        fields = (
            "public_id",
            "focus_type",
            "target",
            "site",
            "status",
            "attention_score",
            "summary",
            "risk_level",
            "payload",
            "last_detected_at",
            "created_at",
            "updated_at",
            "latest_recommendation",
        )

    def get_target(self, obj):
        return {
            "entity_type": obj.target_entity_type,
            "entity_id": obj.target_entity_id,
            "display_label": obj.display_label,
            "client_name": getattr(obj.client, "display_name", ""),
            "contract_number": getattr(obj.contract, "contract_number", ""),
            "technician_name": getattr(obj.technician, "display_name", "") or getattr(obj.technician, "email", ""),
        }

    def get_site(self, obj):
        if obj.site is None:
            return None
        return {
            "public_id": str(obj.site.public_id),
            "name": obj.site.name,
            "code": obj.site.code,
        }


class AgentMarketplaceRequestFlagSerializer(serializers.ModelSerializer):
    latest_recommendation = AgentRecommendationSerializer(read_only=True)
    service_request = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()

    class Meta:
        model = AgentMarketplaceRequestFlag
        fields = (
            "public_id",
            "service_request",
            "site",
            "status",
            "attention_score",
            "summary",
            "risk_level",
            "payload",
            "last_detected_at",
            "created_at",
            "updated_at",
            "latest_recommendation",
        )

    def get_service_request(self, obj):
        return {
            "public_id": str(obj.service_request.public_id),
            "title": obj.service_request.title,
            "priority": obj.service_request.priority,
            "status": obj.service_request.status,
            "city": obj.service_request.city,
            "state": obj.service_request.state,
        }

    def get_site(self, obj):
        if obj.site is None:
            return None
        return {
            "public_id": str(obj.site.public_id),
            "name": obj.site.name,
            "code": obj.site.code,
        }


class AgentAnomalyAttentionFlagSerializer(serializers.ModelSerializer):
    latest_recommendation = AgentRecommendationSerializer(read_only=True)
    target = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()

    class Meta:
        model = AgentAnomalyAttentionFlag
        fields = (
            "public_id",
            "focus_type",
            "target",
            "site",
            "status",
            "attention_score",
            "summary",
            "risk_level",
            "payload",
            "last_detected_at",
            "created_at",
            "updated_at",
            "latest_recommendation",
        )

    def get_target(self, obj):
        return {
            "entity_type": obj.target_entity_type,
            "entity_id": obj.target_entity_id,
            "display_label": obj.display_label,
            "asset_tag": getattr(obj.asset, "asset_tag", ""),
            "client_name": getattr(obj.client, "display_name", ""),
            "contract_number": getattr(obj.contract, "contract_number", ""),
            "technician_name": getattr(obj.technician, "display_name", "") or getattr(obj.technician, "email", ""),
            "part_code": getattr(obj.part, "code", ""),
        }

    def get_site(self, obj):
        if obj.site is None:
            return None
        return {
            "public_id": str(obj.site.public_id),
            "name": obj.site.name,
            "code": obj.site.code,
        }


class ManagerCopilotConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerCopilotConfiguration
        fields = (
            "public_id",
            "is_enabled",
            "default_suggestions",
            "behavior_config",
            "created_at",
            "updated_at",
        )


class ManagerCopilotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerCopilotMessage
        fields = (
            "public_id",
            "role",
            "content",
            "detected_intent",
            "context_snapshot",
            "referenced_agents",
            "structured_payload",
            "created_at",
        )


class ManagerCopilotSessionSerializer(serializers.ModelSerializer):
    messages = ManagerCopilotMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ManagerCopilotSession
        fields = (
            "public_id",
            "status",
            "title",
            "current_context",
            "last_intent",
            "last_query",
            "message_count",
            "last_activity_at",
            "created_at",
            "updated_at",
            "messages",
        )


class ManagerCopilotQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    session_public_id = serializers.UUIDField(required=False, allow_null=True)
    context_seed = serializers.JSONField(required=False)


class ManagerCopilotSessionResetSerializer(serializers.Serializer):
    session_public_id = serializers.UUIDField()


class AtlasLeadSerializer(serializers.ModelSerializer):
    """DEPRECATED: serializer apenas para compatibilidade do modelo AtlasLead legado."""

    class Meta:
        from apps.ai_agents_center.models import AtlasLead
        model = AtlasLead
        fields = (
            "public_id",
            "razao_social",
            "segmento",
            "cidade",
            "regiao",
            "fit_comercial",
            "score",
            "nome_decisor",
            "cargo_decisor",
            "email_contato",
            "telefone",
            "status",
            "notas",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at", "status")
