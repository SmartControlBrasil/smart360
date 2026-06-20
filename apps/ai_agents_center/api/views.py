from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_agents_center.api.serializers import (
    AIBriefingGenerateSerializer,
    AIBriefingSerializer,
    AgentActionProposalSerializer,
    AgentAnomalyAttentionFlagSerializer,
    AgentAssetAttentionFlagSerializer,
    AgentDefinitionSerializer,
    AgentMarketplaceRequestFlagSerializer,
    AgentManualRunSerializer,
    AgentMemoryEntrySerializer,
    AgentProfitabilityAttentionFlagSerializer,
    AgentRecommendationSerializer,
    AgentRunSerializer,
    AgentScheduleHealthFlagSerializer,
    CommercialOpportunitySerializer,
    AtlasProspectImportBatchSerializer,
    AtlasProspectImportSerializer,
    ManagerCopilotMessageSerializer,
    ManagerCopilotQuerySerializer,
    ManagerCopilotSessionSerializer,
    ManagerCopilotSessionResetSerializer,
    ProposalDecisionSerializer,
)
from apps.ai_agents_center.models import (
    AIBriefing,
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentDefinition,
    AgentMarketplaceRequestFlag,
    AgentMemoryEntry,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
    CommercialOpportunity,
    ManagerCopilotSession,
)
from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.ai_agents_center.services.atlas_importer import AtlasImporterService
from apps.ai_agents_center.services.manager_copilot import ManagerCopilotService
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService
from apps.companies.models import Membership
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import OperationalSite


class AIAgentsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = None
        company_id = request.query_params.get("company") or request.data.get("company")
        if company_id:
            company = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = company.company if company else None
        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug="ai_agents_admin",
            action_slug=getattr(view, "permission_action", "manage" if request.method not in permissions.SAFE_METHODS else "view"),
            company=company,
            module_name="ai_agents_center",
            resource_type="ai_agent_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedAIAgentsMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, field_name):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        filter_kwargs = {f"{field_name}__in": company_ids}
        return queryset.filter(**filter_kwargs)


def _resolve_api_tenant_context(request):
    company = None
    site = None
    company_id = request.query_params.get("company") or request.data.get("company")
    if company_id:
        membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
        company = membership.company if membership else None
    if company is None:
        primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
        company = primary_membership.company if primary_membership else None
    site_id = request.query_params.get("site") or request.data.get("site")
    if site_id and company is not None:
        site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
    return {"company": company, "site": site}


class AgentDefinitionViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AgentDefinition.objects.select_related("execution_policy").all()
    serializer_class = AgentDefinitionSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("domain", "status", "enabled")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        definition = self.get_object()
        run = AgentCoordinatorService.run_agent(
            agent_slug=definition.slug,
            company=Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first().company
            if Membership.objects.filter(user=request.user, is_primary=True).exists()
            else None,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.API,
            trigger_reference=request.data.get("trigger_reference", ""),
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AIBriefingViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AIBriefingSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("briefing_type", "audience", "status", "company", "site")
    ordering_fields = ("generated_at", "delivered_at", "viewed_at")

    def get_queryset(self):
        queryset = AIBriefing.objects.select_related("company", "site", "user").prefetch_related("deliveries").all()
        queryset = self._apply_company_scope(queryset, "company")
        audience = self.request.query_params.get("audience")
        if audience:
            queryset = queryset.filter(audience=audience)
        return queryset


class AgentRunViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentRunSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("agent", "company", "site", "trigger_type", "status")
    search_fields = ("agent__name", "trigger_reference", "output_summary", "error_message")
    ordering_fields = ("created_at", "started_at", "finished_at", "duration_ms")

    def get_queryset(self):
        queryset = AgentRun.objects.select_related("agent", "company", "site", "triggered_by").all()
        queryset = self._apply_company_scope(queryset, "company")
        agent_slug = self.request.query_params.get("agent_slug")
        if agent_slug:
            queryset = queryset.filter(agent__slug=agent_slug)
        return queryset


class AgentRecommendationViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentRecommendationSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("company", "site", "recommendation_type", "severity", "status", "entity_type")
    search_fields = ("title", "summary", "entity_id")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "company", "site").all()
        queryset = self._apply_company_scope(queryset, "company")
        agent_slug = self.request.query_params.get("agent_slug")
        asset_public_id = self.request.query_params.get("asset")
        category_slug = self.request.query_params.get("category")
        technician_id = self.request.query_params.get("technician")
        client_public_id = self.request.query_params.get("client")
        contract_public_id = self.request.query_params.get("contract")
        request_public_id = self.request.query_params.get("request")
        specialty = self.request.query_params.get("specialty")
        target_date = self.request.query_params.get("date")
        if agent_slug:
            queryset = queryset.filter(agent_run__agent__slug=agent_slug)
        if asset_public_id:
            queryset = queryset.filter(entity_type="asset", entity_id=asset_public_id)
        if technician_id:
            queryset = queryset.filter(
                Q(entity_type="user", entity_id=str(technician_id))
                | Q(payload__technician__technician_id=int(technician_id))
            )
        if client_public_id:
            queryset = queryset.filter(
                Q(entity_type="maintenance_client", entity_id=client_public_id)
                | Q(payload__client_public_id=client_public_id)
            )
        if contract_public_id:
            queryset = queryset.filter(
                Q(entity_type="maintenance_contract", entity_id=contract_public_id)
                | Q(payload__contract_public_id=contract_public_id)
            )
        if request_public_id:
            queryset = queryset.filter(
                Q(entity_type="technician_service_request", entity_id=request_public_id)
                | Q(payload__service_request_public_id=request_public_id)
            )
        if specialty:
            queryset = queryset.filter(
                Q(summary__icontains=specialty)
                | Q(title__icontains=specialty)
                | Q(payload__category=specialty)
            )
        if target_date:
            queryset = queryset.filter(
                Q(agent_run__input_context__target_date=target_date)
                | Q(payload__technician__date=target_date)
            )
        if category_slug:
            queryset = queryset.filter(
                Q(agent_run__input_context__category_slug=category_slug)
                | Q(payload__asset__category_slug=category_slug)
            )
        return queryset.distinct()


class AgentActionProposalViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentActionProposalSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "action_type", "target_entity")
    search_fields = ("action_type", "target_entity_id")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = AgentActionProposal.objects.select_related("agent_run", "agent_run__agent", "agent_run__company").all()
        queryset = self._apply_company_scope(queryset, "agent_run__company")
        agent_slug = self.request.query_params.get("agent_slug")
        asset_public_id = self.request.query_params.get("asset")
        technician_id = self.request.query_params.get("technician")
        client_public_id = self.request.query_params.get("client")
        contract_public_id = self.request.query_params.get("contract")
        request_public_id = self.request.query_params.get("request")
        target_date = self.request.query_params.get("date")
        if agent_slug:
            queryset = queryset.filter(agent_run__agent__slug=agent_slug)
        if asset_public_id:
            queryset = queryset.filter(target_entity="asset", target_entity_id=asset_public_id)
        if technician_id:
            queryset = queryset.filter(
                Q(proposed_payload__technician_id=int(technician_id))
                | Q(proposed_payload__from_technician_id=int(technician_id))
                | Q(proposed_payload__to_technician_id=int(technician_id))
            )
        if client_public_id:
            queryset = queryset.filter(
                Q(target_entity="maintenance_client", target_entity_id=client_public_id)
                | Q(proposed_payload__client_public_id=client_public_id)
            )
        if contract_public_id:
            queryset = queryset.filter(
                Q(target_entity="maintenance_contract", target_entity_id=contract_public_id)
                | Q(proposed_payload__contract_public_id=contract_public_id)
            )
        if request_public_id:
            queryset = queryset.filter(
                Q(target_entity="technician_service_request", target_entity_id=request_public_id)
                | Q(proposed_payload__service_request_public_id=request_public_id)
            )
        if target_date:
            queryset = queryset.filter(
                Q(proposed_payload__date=target_date) | Q(agent_run__input_context__target_date=target_date)
            )
        return queryset

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        proposal = self.get_object()
        AgentCoordinatorService.approve_proposal(proposal=proposal, approved_by=request.user, company=proposal.agent_run.company)
        return Response(AgentActionProposalSerializer(proposal).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        proposal = self.get_object()
        serializer = ProposalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AgentCoordinatorService.reject_proposal(
            proposal=proposal,
            rejected_by=request.user,
            company=proposal.agent_run.company,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(AgentActionProposalSerializer(proposal).data, status=status.HTTP_200_OK)


class CommercialOpportunityViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CommercialOpportunitySerializer
    permission_classes = [AIAgentsPermission]
    lookup_field = "public_id"
    filterset_fields = ("status", "source", "segment", "city", "state", "company")
    search_fields = ("company_name", "title", "opportunity_description", "recommended_product", "recommended_solution")
    ordering_fields = ("created_at", "updated_at", "confidence_score", "commercial_score")

    def get_queryset(self):
        queryset = CommercialOpportunity.objects.select_related("company", "lead", "agent_run").all()
        queryset = self._apply_company_scope(queryset, "company")
        status_filter = self.request.query_params.get("status")
        source = self.request.query_params.get("source")
        segment = self.request.query_params.get("segment")
        city = self.request.query_params.get("city")
        state = self.request.query_params.get("state")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if source:
            queryset = queryset.filter(source=source)
        if segment:
            queryset = queryset.filter(segment__icontains=segment)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if state:
            queryset = queryset.filter(state__iexact=state)
        return queryset

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[AIAgentsPermission])
    def approve(self, request, public_id=None):
        self.permission_action = "approve"
        opportunity = self.get_object()
        try:
            OpportunityBuilderService.approve(opportunity=opportunity, user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(opportunity).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject", permission_classes=[AIAgentsPermission])
    def reject(self, request, public_id=None):
        self.permission_action = "approve"
        opportunity = self.get_object()
        try:
            OpportunityBuilderService.reject(
                opportunity=opportunity,
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(opportunity).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="convert-to-lead", permission_classes=[AIAgentsPermission])
    def convert_to_lead(self, request, public_id=None):
        self.permission_action = "approve"
        opportunity = self.get_object()
        try:
            lead = OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        opportunity.refresh_from_db()
        payload = self.get_serializer(opportunity).data
        payload["lead_public_id"] = str(lead.public_id)
        return Response(payload, status=status.HTTP_200_OK)


class AtlasProspectImportView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        serializer = AtlasProspectImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.validated_data["company"]
        membership = Membership.objects.filter(user=request.user, company=company).first()
        if membership is None and not getattr(request.user, "is_superuser", False):
            return Response({"detail": "Company not accessible for current user."}, status=status.HTTP_403_FORBIDDEN)
        batch = AtlasImporterService.import_rows(
            rows=serializer.validated_data["rows"],
            company=company,
            source=serializer.validated_data.get("source", CommercialOpportunity.Source.MANUAL),
            filename=serializer.validated_data.get("filename", ""),
            created_by=request.user,
        )
        return Response(AtlasProspectImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)



class AgentMemoryEntryViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentMemoryEntrySerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("agent", "company", "site", "memory_kind", "entity_type")
    search_fields = ("entity_id", "content")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = AgentMemoryEntry.objects.select_related("agent", "company", "site").all()
        return self._apply_company_scope(queryset, "company")


class AgentAssetAttentionFlagViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentAssetAttentionFlagSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "risk_level", "company", "site")
    search_fields = ("asset__asset_tag", "asset__name", "summary")
    ordering_fields = ("attention_score", "updated_at", "created_at")

    def get_queryset(self):
        queryset = AgentAssetAttentionFlag.objects.select_related(
            "agent",
            "company",
            "site",
            "asset",
            "asset__category",
            "latest_recommendation",
            "latest_recommendation__agent_run",
            "latest_recommendation__agent_run__agent",
        ).filter(agent__slug="maintenance-agent")
        queryset = self._apply_company_scope(queryset, "company")
        site_id = self.request.query_params.get("site")
        category_slug = self.request.query_params.get("category")
        asset_public_id = self.request.query_params.get("asset")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        if category_slug:
            queryset = queryset.filter(asset__category__slug=category_slug)
        if asset_public_id:
            queryset = queryset.filter(asset__public_id=asset_public_id)
        return queryset


class AgentScheduleHealthFlagViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentScheduleHealthFlagSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "risk_level", "flag_type", "company", "site", "schedule_date")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "summary")
    ordering_fields = ("attention_score", "schedule_date", "updated_at")

    def get_queryset(self):
        queryset = AgentScheduleHealthFlag.objects.select_related(
            "agent",
            "company",
            "site",
            "technician",
            "latest_recommendation",
            "latest_recommendation__agent_run",
            "latest_recommendation__agent_run__agent",
        ).filter(agent__slug="scheduling-agent")
        queryset = self._apply_company_scope(queryset, "company")
        technician_id = self.request.query_params.get("technician")
        site_id = self.request.query_params.get("site")
        target_date = self.request.query_params.get("date")
        if technician_id:
            queryset = queryset.filter(technician_id=technician_id)
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        if target_date:
            queryset = queryset.filter(schedule_date=target_date)
        return queryset


class AgentProfitabilityAttentionFlagViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentProfitabilityAttentionFlagSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "risk_level", "focus_type", "company", "site")
    search_fields = ("display_label", "summary", "target_entity_type", "target_entity_id")
    ordering_fields = ("attention_score", "updated_at", "created_at")

    def get_queryset(self):
        queryset = AgentProfitabilityAttentionFlag.objects.select_related(
            "agent",
            "company",
            "site",
            "client",
            "contract",
            "technician",
            "latest_recommendation",
            "latest_recommendation__agent_run",
            "latest_recommendation__agent_run__agent",
        ).filter(agent__slug="profitability-agent")
        queryset = self._apply_company_scope(queryset, "company")
        site_id = self.request.query_params.get("site")
        client_public_id = self.request.query_params.get("client")
        contract_public_id = self.request.query_params.get("contract")
        technician_id = self.request.query_params.get("technician")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        if client_public_id:
            queryset = queryset.filter(client__public_id=client_public_id)
        if contract_public_id:
            queryset = queryset.filter(contract__public_id=contract_public_id)
        if technician_id:
            queryset = queryset.filter(technician_id=technician_id)
        return queryset


class AgentMarketplaceRequestFlagViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentMarketplaceRequestFlagSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "risk_level", "company", "site")
    search_fields = ("service_request__title", "summary", "service_request__city", "service_request__state")
    ordering_fields = ("attention_score", "updated_at", "created_at")

    def get_queryset(self):
        queryset = AgentMarketplaceRequestFlag.objects.select_related(
            "agent",
            "company",
            "site",
            "service_request",
            "latest_recommendation",
            "latest_recommendation__agent_run",
            "latest_recommendation__agent_run__agent",
        ).filter(agent__slug="marketplace-agent")
        queryset = self._apply_company_scope(queryset, "company")
        site_id = self.request.query_params.get("site")
        request_public_id = self.request.query_params.get("request")
        specialty = self.request.query_params.get("specialty")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        if request_public_id:
            queryset = queryset.filter(service_request__public_id=request_public_id)
        if specialty:
            queryset = queryset.filter(service_request__category__iexact=specialty)
        return queryset


class AgentAnomalyAttentionFlagViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentAnomalyAttentionFlagSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status", "risk_level", "focus_type", "company", "site")
    search_fields = ("display_label", "summary", "target_entity_type", "target_entity_id")
    ordering_fields = ("attention_score", "updated_at", "created_at")

    def get_queryset(self):
        queryset = AgentAnomalyAttentionFlag.objects.select_related(
            "agent",
            "company",
            "site",
            "asset",
            "client",
            "contract",
            "technician",
            "part",
            "latest_recommendation",
            "latest_recommendation__agent_run",
            "latest_recommendation__agent_run__agent",
        ).filter(agent__slug="anomaly-agent")
        queryset = self._apply_company_scope(queryset, "company")
        site_id = self.request.query_params.get("site")
        asset_public_id = self.request.query_params.get("asset")
        client_public_id = self.request.query_params.get("client")
        contract_public_id = self.request.query_params.get("contract")
        technician_id = self.request.query_params.get("technician")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        if asset_public_id:
            queryset = queryset.filter(asset__public_id=asset_public_id)
        if client_public_id:
            queryset = queryset.filter(client__public_id=client_public_id)
        if contract_public_id:
            queryset = queryset.filter(contract__public_id=contract_public_id)
        if technician_id:
            queryset = queryset.filter(technician_id=technician_id)
        return queryset


class ManagerCopilotSessionViewSet(ScopedAIAgentsMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ManagerCopilotSessionSerializer
    permission_classes = [AIAgentsPermission]
    filterset_fields = ("status",)
    search_fields = ("title", "last_query", "last_intent")
    ordering_fields = ("created_at", "updated_at", "last_activity_at")

    def get_queryset(self):
        queryset = ManagerCopilotSession.objects.select_related("company", "site", "user").prefetch_related("messages").filter(user=self.request.user)
        return self._apply_company_scope(queryset, "company")

    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        session = self.get_object()
        ManagerCopilotService.reset_session(session=session, user=request.user)
        return Response(ManagerCopilotSessionSerializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        session = self.get_object()
        return Response(ManagerCopilotMessageSerializer(session.messages.order_by("created_at"), many=True).data, status=status.HTTP_200_OK)


class AgentManualRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        serializer = AgentManualRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = AgentCoordinatorService.run_agent(
            agent_slug=serializer.validated_data["agent_slug"],
            company=serializer.validated_data.get("company"),
            site=serializer.validated_data.get("site"),
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=serializer.validated_data.get("trigger_reference", ""),
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class MaintenanceAnalysisRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        site = None
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        if company is None:
            primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
            company = primary_membership.company if primary_membership else None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
        trigger_reference = request.data.get("trigger_reference", "")
        asset_public_id = request.data.get("asset_public_id")
        category_slug = request.data.get("category_slug")
        if asset_public_id:
            trigger_reference = f"asset:{asset_public_id}"
        elif category_slug:
            trigger_reference = f"category:{category_slug}"
        run = AgentCoordinatorService.run_agent(
            agent_slug="maintenance-agent",
            company=company,
            site=site,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=trigger_reference,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class SchedulingAnalysisRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        if company is None:
            primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
            company = primary_membership.company if primary_membership else None
        site = None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
        trigger_reference = request.data.get("trigger_reference", "")
        technician_id = request.data.get("technician_id")
        target_date = request.data.get("date")
        if technician_id and target_date:
            trigger_reference = f"technician:{technician_id}:date:{target_date}"
        elif target_date and site is not None:
            trigger_reference = f"site:{site.code}:date:{target_date}"
        elif target_date:
            trigger_reference = f"date:{target_date}"
        run = AgentCoordinatorService.run_agent(
            agent_slug="scheduling-agent",
            company=company,
            site=site,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=trigger_reference,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ProfitabilityAnalysisRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        if company is None:
            primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
            company = primary_membership.company if primary_membership else None
        site = None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
        trigger_reference = request.data.get("trigger_reference", "")
        client_public_id = request.data.get("client_public_id")
        contract_public_id = request.data.get("contract_public_id")
        technician_id = request.data.get("technician_id")
        target_date = request.data.get("date")
        if client_public_id:
            trigger_reference = f"client:{client_public_id}"
        elif contract_public_id:
            trigger_reference = f"contract:{contract_public_id}"
        elif technician_id and target_date:
            trigger_reference = f"technician:{technician_id}:date:{target_date}"
        elif site is not None:
            trigger_reference = trigger_reference or f"site:{site.code}"
        elif target_date:
            trigger_reference = f"date:{target_date}"
        run = AgentCoordinatorService.run_agent(
            agent_slug="profitability-agent",
            company=company,
            site=site,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=trigger_reference,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class MarketplaceAnalysisRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        if company is None:
            primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
            company = primary_membership.company if primary_membership else None
        site = None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
        trigger_reference = request.data.get("trigger_reference", "")
        request_public_id = request.data.get("service_request_public_id")
        specialty = request.data.get("specialty")
        target_date = request.data.get("date")
        if request_public_id:
            trigger_reference = f"request:{request_public_id}"
        elif site is not None:
            trigger_reference = f"site:{site.code}"
        elif specialty:
            trigger_reference = f"category:{specialty}"
        elif target_date:
            trigger_reference = f"date:{target_date}"
        run = AgentCoordinatorService.run_agent(
            agent_slug="marketplace-agent",
            company=company,
            site=site,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=trigger_reference,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AnomalyAnalysisRunView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        if company is None:
            primary_membership = Membership.objects.filter(user=request.user, is_primary=True).select_related("company").first()
            company = primary_membership.company if primary_membership else None
        site = None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(pk=site_id, maintenance_client__company=company).first()
        trigger_reference = request.data.get("trigger_reference", "")
        asset_public_id = request.data.get("asset_public_id")
        client_public_id = request.data.get("client_public_id")
        contract_public_id = request.data.get("contract_public_id")
        technician_id = request.data.get("technician_id")
        part_public_id = request.data.get("part_public_id")
        if asset_public_id:
            trigger_reference = f"asset:{asset_public_id}"
        elif client_public_id:
            trigger_reference = f"client:{client_public_id}"
        elif contract_public_id:
            trigger_reference = f"contract:{contract_public_id}"
        elif technician_id:
            trigger_reference = f"technician:{technician_id}"
        elif part_public_id:
            trigger_reference = f"part:{part_public_id}"
        elif site is not None:
            trigger_reference = trigger_reference or f"site:{site.code}"
        run = AgentCoordinatorService.run_agent(
            agent_slug="anomaly-agent",
            company=company,
            site=site,
            triggered_by=request.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            trigger_reference=trigger_reference,
        )
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)


class AIBriefingGenerateView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "manage"

    def post(self, request, *args, **kwargs):
        serializer = AIBriefingGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_context = _resolve_api_tenant_context(request)
        company = serializer.validated_data.get("company") or tenant_context.get("company")
        site = serializer.validated_data.get("site") or tenant_context.get("site")
        target_user = request.user
        if serializer.validated_data.get("user_id"):
            from apps.users.models import User

            target_user = User.objects.filter(pk=serializer.validated_data["user_id"]).first() or request.user
        briefing = AIBriefingComposer.generate_briefing(
            briefing_type=serializer.validated_data["briefing_type"],
            audience=serializer.validated_data["audience"],
            company=company,
            site=site,
            user=target_user,
            start=serializer.validated_data.get("start"),
            end=serializer.validated_data.get("end"),
            filters={"source": "api"},
        )
        AIBriefingComposer.deliver_briefing(briefing=briefing)
        return Response(AIBriefingSerializer(briefing).data, status=status.HTTP_201_CREATED)


class ManagerCopilotQueryView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "view"

    def post(self, request, *args, **kwargs):
        serializer = ManagerCopilotQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_context = _resolve_api_tenant_context(request)
        payload = ManagerCopilotService.handle_query(
            user=request.user,
            tenant_context=tenant_context,
            query=serializer.validated_data["query"],
            session_public_id=serializer.validated_data.get("session_public_id"),
            context_seed=serializer.validated_data.get("context_seed") or {},
        )
        return Response(
            {
                "session": ManagerCopilotSessionSerializer(payload["session"]).data,
                "context": payload["context"],
                "response": payload["response"],
                "suggestions": payload["suggestions"],
            },
            status=status.HTTP_200_OK,
        )


class ManagerCopilotContextView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        tenant_context = _resolve_api_tenant_context(request)
        payload = ManagerCopilotService.get_current_context_payload(
            user=request.user,
            tenant_context=tenant_context,
            session_public_id=request.query_params.get("session_public_id"),
        )
        return Response(
            {
                "session": ManagerCopilotSessionSerializer(payload["session"]).data,
                "context": payload["context"],
                "suggestions": payload["suggestions"],
            },
            status=status.HTTP_200_OK,
        )


class ManagerCopilotSuggestionsView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        tenant_context = _resolve_api_tenant_context(request)
        payload = ManagerCopilotService.get_current_context_payload(
            user=request.user,
            tenant_context=tenant_context,
            session_public_id=request.query_params.get("session_public_id"),
        )
        return Response({"suggestions": payload["suggestions"]}, status=status.HTTP_200_OK)


class ManagerCopilotRecommendationsView(APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        tenant_context = _resolve_api_tenant_context(request)
        recommendations = ManagerCopilotService.list_relevant_recommendations(
            user=request.user,
            tenant_context=tenant_context,
            session_public_id=request.query_params.get("session_public_id"),
        )
        return Response({"recommendations": recommendations}, status=status.HTTP_200_OK)


class ManagerCopilotProposalApproveView(ScopedAIAgentsMixin, APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "approve"

    def post(self, request, proposal_public_id, *args, **kwargs):
        queryset = self._apply_company_scope(
            AgentActionProposal.objects.select_related("agent_run", "agent_run__company"),
            "agent_run__company",
        )
        proposal = queryset.filter(public_id=proposal_public_id).first()
        if proposal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        AgentCoordinatorService.approve_proposal(proposal=proposal, approved_by=request.user, company=proposal.agent_run.company)
        SystemEventService.log_system_event(
            event_type="copilot.manager.proposal.approved",
            source_module="ai_agents_center",
            message="Proposal approved from manager copilot.",
            entity_type=proposal.target_entity,
            entity_id=proposal.target_entity_id,
            user=request.user,
            company=proposal.agent_run.company,
            site=proposal.agent_run.site,
            payload={"proposal_public_id": str(proposal.public_id), "action_type": proposal.action_type},
        )
        return Response(AgentActionProposalSerializer(proposal).data, status=status.HTTP_200_OK)


class ManagerCopilotProposalRejectView(ScopedAIAgentsMixin, APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "approve"

    def post(self, request, proposal_public_id, *args, **kwargs):
        serializer = ProposalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = self._apply_company_scope(
            AgentActionProposal.objects.select_related("agent_run", "agent_run__company"),
            "agent_run__company",
        )
        proposal = queryset.filter(public_id=proposal_public_id).first()
        if proposal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        AgentCoordinatorService.reject_proposal(
            proposal=proposal,
            rejected_by=request.user,
            company=proposal.agent_run.company,
            reason=serializer.validated_data.get("reason", ""),
        )
        SystemEventService.log_system_event(
            event_type="copilot.manager.proposal.rejected",
            source_module="ai_agents_center",
            message="Proposal rejected from manager copilot.",
            entity_type=proposal.target_entity,
            entity_id=proposal.target_entity_id,
            user=request.user,
            company=proposal.agent_run.company,
            site=proposal.agent_run.site,
            payload={
                "proposal_public_id": str(proposal.public_id),
                "action_type": proposal.action_type,
                "reason": serializer.validated_data.get("reason", ""),
            },
        )
        return Response(AgentActionProposalSerializer(proposal).data, status=status.HTTP_200_OK)


class AIBriefingViewedView(ScopedAIAgentsMixin, APIView):
    permission_classes = [AIAgentsPermission]
    permission_action = "view"

    def post(self, request, briefing_public_id, *args, **kwargs):
        queryset = self._apply_company_scope(AIBriefing.objects.select_related("company", "site", "user"), "company")
        briefing = queryset.filter(public_id=briefing_public_id).first()
        if briefing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        AIBriefingComposer.mark_viewed(briefing=briefing, user=request.user)
        return Response(AIBriefingSerializer(briefing).data, status=status.HTTP_200_OK)
