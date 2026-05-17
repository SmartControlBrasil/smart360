from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_simulation_engine.api.serializers import (
    SimulationRequestSerializer,
    SimulationRunSerializer,
    SimulationScenarioSerializer,
    SimulationTypeSerializer,
)
from apps.ai_simulation_engine.models import SimulationRun, SimulationScenario, SimulationType
from apps.ai_simulation_engine.services.orchestrator import SimulationOrchestrator
from apps.companies.models import Membership
from apps.observability_center.services.observability_service import SystemEventService


class AISimulationPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = None
        company_id = request.query_params.get("company") or request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug="ai_agents_admin",
            action_slug=getattr(view, "permission_action", "manage" if request.method not in permissions.SAFE_METHODS else "view"),
            company=company,
            module_name="ai_simulation_engine",
            resource_type="ai_simulation_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedSimulationMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, company_field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{company_field}__in": company_ids}) | Q(**{f"{company_field}__isnull": True}))


class SimulationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SimulationType.objects.filter(enabled=True)
    serializer_class = SimulationTypeSerializer
    permission_classes = [AISimulationPermission]
    lookup_field = "public_id"


class SimulationScenarioViewSet(ScopedSimulationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SimulationScenarioSerializer
    permission_classes = [AISimulationPermission]
    lookup_field = "public_id"
    filterset_fields = ("status", "simulation_type", "company", "site", "target_entity")
    search_fields = ("title", "description", "target_entity_id")

    def get_queryset(self):
        queryset = SimulationScenario.objects.select_related("simulation_type", "company", "site", "created_by_user").prefetch_related("runs__result")
        return self._apply_company_scope(queryset)

    @action(detail=False, methods=["post"])
    def request(self, request, *args, **kwargs):
        serializer = SimulationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = None
        if serializer.validated_data.get("decision_public_id"):
            decision = AgentDecision.objects.select_related("company", "site", "agent_action_proposal").get(
                public_id=serializer.validated_data["decision_public_id"]
            )
            simulation_run = SimulationOrchestrator.simulate_for_decision(decision=decision, requested_by=request.user, force=True)
            return Response(SimulationRunSerializer(simulation_run).data, status=status.HTTP_201_CREATED)
        simulation_type = SimulationType.objects.get(slug=serializer.validated_data["simulation_type"], enabled=True)
        scenario = SimulationScenario.objects.create(
            simulation_type=simulation_type,
            company=serializer.validated_data.get("company"),
            site=serializer.validated_data.get("site"),
            title=serializer.validated_data.get("title") or simulation_type.name,
            description=serializer.validated_data.get("description", ""),
            target_entity=serializer.validated_data.get("target_entity", ""),
            target_entity_id=serializer.validated_data.get("target_entity_id", ""),
            status=SimulationScenario.ScenarioStatus.READY,
            created_by_user=request.user,
        )
        simulation_run = SimulationRun.objects.create(
            scenario=scenario,
            trigger_type=SimulationRun.TriggerType.API,
            source_type=SimulationRun.SourceType.DIRECT,
            input_payload=serializer.validated_data.get("input_payload", {}),
            created_by_user=request.user,
        )
        simulation_run = SimulationOrchestrator.run(simulation_run=simulation_run)
        return Response(SimulationRunSerializer(simulation_run).data, status=status.HTTP_201_CREATED)


class SimulationRunViewSet(ScopedSimulationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SimulationRunSerializer
    permission_classes = [AISimulationPermission]
    lookup_field = "public_id"
    filterset_fields = ("status", "trigger_type", "source_type", "decision")
    search_fields = ("source_reference", "scenario__title")

    def get_queryset(self):
        queryset = SimulationRun.objects.select_related("scenario", "scenario__simulation_type", "scenario__company", "scenario__site", "decision", "created_by_user", "result")
        return self._apply_company_scope(queryset, company_field="scenario__company_id")

    @action(detail=True, methods=["get"])
    def compare(self, request, *args, **kwargs):
        simulation_run = self.get_object()
        result = getattr(simulation_run, "result", None)
        SystemEventService.log_system_event(
            event_type="simulation.viewed",
            source_module="ai_simulation_engine",
            message="Simulation comparison viewed.",
            entity_type=simulation_run.scenario.target_entity or simulation_run.scenario.simulation_type.slug,
            entity_id=simulation_run.scenario.target_entity_id or str(simulation_run.public_id),
            user=request.user,
            company=simulation_run.scenario.company,
            site=simulation_run.scenario.site,
            payload={"simulation_run_public_id": str(simulation_run.public_id)},
        )
        comparison = {
            "baseline_snapshot": simulation_run.baseline_snapshot,
            "current": (result.result_payload or {}).get("current", {}) if result else {},
            "proposed": (result.result_payload or {}).get("proposed", {}) if result else {},
            "gains": (result.result_payload or {}).get("gains", []) if result else [],
            "tradeoffs": (result.result_payload or {}).get("tradeoffs", []) if result else [],
            "assumptions": (result.result_payload or {}).get("assumptions", []) if result else [],
            "summary": result.summary if result else "",
            "recommendation": result.recommendation if result else "",
            "confidence_level": result.confidence_level if result else "",
        }
        return Response(comparison, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def by_entity(self, request, *args, **kwargs):
        entity = request.query_params.get("entity", "")
        entity_id = request.query_params.get("entity_id", "")
        queryset = self.filter_queryset(self.get_queryset().filter(scenario__target_entity=entity, scenario__target_entity_id=entity_id))
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"])
    def attach_to_decision(self, request, *args, **kwargs):
        simulation_run = self.get_object()
        decision_public_id = request.data.get("decision_public_id")
        decision = AgentDecision.objects.select_related("company", "site").get(public_id=decision_public_id)
        simulation_run.decision = decision
        simulation_run.source_type = SimulationRun.SourceType.DECISION
        simulation_run.source_reference = str(decision.public_id)
        simulation_run.save(update_fields=["decision", "source_type", "source_reference", "updated_at"])
        if hasattr(simulation_run, "result"):
            explainability_payload = dict(decision.explainability_payload or {})
            explainability_payload["simulation"] = {
                "simulation_run_public_id": str(simulation_run.public_id),
                "simulation_type": simulation_run.scenario.simulation_type.slug,
                "summary": simulation_run.result.summary,
                "confidence_level": simulation_run.result.confidence_level,
            }
            decision.explainability_payload = explainability_payload
            decision.save(update_fields=["explainability_payload", "updated_at"])
        return Response(self.get_serializer(simulation_run).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="copilot-summary")
    def copilot_summary(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(status=SimulationRun.RunStatus.COMPLETED).order_by("-created_at")[:8])
        summaries = [
            {
                "simulation_type": item.scenario.simulation_type.slug,
                "summary": item.result.summary if hasattr(item, "result") else "",
                "confidence_level": item.result.confidence_level if hasattr(item, "result") else "",
                "impact_score": str(item.result.impact_score) if hasattr(item, "result") else "0",
                "decision_public_id": str(item.decision.public_id) if item.decision_id else "",
            }
            for item in queryset
        ]
        return Response({"results": summaries}, status=status.HTTP_200_OK)
