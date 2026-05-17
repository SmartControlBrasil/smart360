from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_optimization_loop.api.serializers import (
    DecisionOutcomeSerializer,
    FeedbackSignalSerializer,
    OptimizationPolicySerializer,
    OptimizationProposalDecisionSerializer,
    OptimizationProposalSerializer,
    RecommendationOutcomeSerializer,
    SimulationOutcomeSerializer,
)
from apps.ai_optimization_loop.models import (
    DecisionOutcome,
    FeedbackSignal,
    OptimizationPolicy,
    OptimizationProposal,
    RecommendationOutcome,
    SimulationOutcome,
)
from apps.ai_optimization_loop.services.approvals import OptimizationApprovalService
from apps.ai_optimization_loop.services.orchestrator import LearningOrchestrator
from apps.ai_optimization_loop.services.quality import OptimizationQualityService
from apps.companies.models import Membership


class AIOptimizationPermission(permissions.BasePermission):
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
            module_name="ai_optimization_loop",
            resource_type="ai_optimization_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedOptimizationMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, company_field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{company_field}__in": company_ids}) | Q(**{f"{company_field}__isnull": True}))


class FeedbackSignalViewSet(ScopedOptimizationMixin, viewsets.ModelViewSet):
    serializer_class = FeedbackSignalSerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    filterset_fields = ("source_type", "signal_type", "company", "site")
    search_fields = ("source_reference", "comment")

    def get_queryset(self):
        return self._apply_company_scope(FeedbackSignal.objects.select_related("company", "site", "user"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        feedback = LearningOrchestrator.register_feedback(
            source_type=validated["source_type"],
            source_reference=validated["source_reference"],
            signal_type=validated["signal_type"],
            score=validated["score"],
            company=validated.get("company"),
            site=validated.get("site"),
            user=self.request.user,
            comment=validated.get("comment", ""),
            metadata=validated.get("metadata", {}),
        )
        output = self.get_serializer(feedback)
        return Response(output.data, status=status.HTTP_201_CREATED)


class RecommendationOutcomeViewSet(ScopedOptimizationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = RecommendationOutcomeSerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    filterset_fields = ("outcome_status", "effectiveness_level", "company", "site")
    search_fields = ("recommendation__title", "observed_effect_summary")

    def get_queryset(self):
        return self._apply_company_scope(RecommendationOutcome.objects.select_related("recommendation", "company", "site"))


class DecisionOutcomeViewSet(ScopedOptimizationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DecisionOutcomeSerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    filterset_fields = ("result_status", "effectiveness_level", "company", "site")
    search_fields = ("decision__normalized_action_type", "evaluation_summary")

    def get_queryset(self):
        return self._apply_company_scope(DecisionOutcome.objects.select_related("decision", "company", "site"))

    @action(detail=True, methods=["get"])
    def comparison(self, request, *args, **kwargs):
        outcome = self.get_object()
        return Response(
            {
                "expected_result": outcome.expected_result,
                "actual_result": outcome.actual_result,
                "effectiveness_score": str(outcome.effectiveness_score),
                "effectiveness_level": outcome.effectiveness_level,
                "evaluation_summary": outcome.evaluation_summary,
            },
            status=status.HTTP_200_OK,
        )


class SimulationOutcomeViewSet(ScopedOptimizationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SimulationOutcomeSerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    filterset_fields = ("result_status", "effectiveness_level", "company", "site")
    search_fields = ("simulation_run__scenario__title", "evaluation_summary")

    def get_queryset(self):
        return self._apply_company_scope(SimulationOutcome.objects.select_related("simulation_run", "company", "site"))


class OptimizationPolicyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OptimizationPolicySerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    queryset = OptimizationPolicy.objects.filter(enabled=True).order_by("target_type", "proposal_type")


class OptimizationProposalViewSet(ScopedOptimizationMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OptimizationProposalSerializer
    permission_classes = [AIOptimizationPermission]
    lookup_field = "public_id"
    filterset_fields = ("status", "target_type", "proposal_type", "risk_level")
    search_fields = ("target_reference", "rationale", "evidence_summary")

    def get_queryset(self):
        return self._apply_company_scope(
            OptimizationProposal.objects.select_related("company", "site", "policy_applied", "approved_by_user").prefetch_related("audit_entries")
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, *args, **kwargs):
        proposal = self.get_object()
        serializer = OptimizationProposalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = OptimizationApprovalService.approve(
            proposal=proposal,
            approved_by=request.user,
            comment=serializer.validated_data.get("comment", ""),
            apply=serializer.validated_data.get("apply", True),
        )
        return Response(self.get_serializer(proposal).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, *args, **kwargs):
        proposal = self.get_object()
        serializer = OptimizationProposalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = OptimizationApprovalService.reject(
            proposal=proposal,
            rejected_by=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(self.get_serializer(proposal).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request, *args, **kwargs):
        company = None
        company_id = request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        generated = LearningOrchestrator.generate_company_proposals(company=company)
        return Response(self.get_serializer(generated, many=True).data, status=status.HTTP_201_CREATED)


class AgentQualityView(APIView):
    permission_classes = [AIOptimizationPermission]
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        company = None
        company_id = request.query_params.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        return Response({"results": OptimizationQualityService.agent_quality(company=company)}, status=status.HTTP_200_OK)


class CopilotQualityView(APIView):
    permission_classes = [AIOptimizationPermission]
    permission_action = "view"

    def get(self, request, *args, **kwargs):
        company = None
        company_id = request.query_params.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        return Response({"results": OptimizationQualityService.copilot_quality(company=company)}, status=status.HTTP_200_OK)
