from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_decision_engine.api.serializers import (
    AgentDecisionSerializer,
    DecisionApprovalCommandSerializer,
    DecisionExecutionSerializer,
    DecisionPolicySerializer,
)
from apps.ai_decision_engine.models import AgentDecision, DecisionExecution, DecisionPolicy
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.companies.models import Membership


class AIDecisionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        company = None
        company_id = request.query_params.get("company") or request.data.get("company")

        if company_id:
            membership = Membership.objects.filter(
                user=request.user,
                company_id=company_id
            ).select_related("company").first()
            company = membership.company if membership else None

        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug="ai_agents_admin",
            action_slug=getattr(
                view,
                "permission_action",
                "approve" if request.method not in permissions.SAFE_METHODS else "view"
            ),
            company=company,
            module_name="ai_decision_engine",
            resource_type="ai_decision_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedDecisionMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(
            Membership.objects.filter(user=self.request.user)
            .values_list("company_id", flat=True)
        )

    def _apply_company_scope(self, queryset):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(company_id__in=company_ids) | Q(company__isnull=True))


class DecisionPolicyViewSet(viewsets.ModelViewSet):
    queryset = DecisionPolicy.objects.all()
    serializer_class = DecisionPolicySerializer
    permission_classes = [AIDecisionPermission]
    permission_action = "manage"
    lookup_field = "public_id"

    filterset_fields = ("action_type", "risk_level", "autonomy_level", "enabled", "tenant_scope_mode")
    search_fields = ("slug", "name", "description")
    ordering_fields = ("action_type", "updated_at", "created_at")
    http_method_names = ["get", "patch", "head", "options"]


class AgentDecisionViewSet(ScopedDecisionMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentDecisionSerializer
    permission_classes = [AIDecisionPermission]
    lookup_field = "public_id"

    filterset_fields = ("decision_status", "risk_level", "normalized_action_type", "company", "site")
    search_fields = ("action_type", "normalized_action_type", "target_entity_id", "decision_reason")
    ordering_fields = ("created_at", "updated_at", "decided_at")

    def get_queryset(self):
        queryset = AgentDecision.objects.select_related(
            "company",
            "site",
            "policy_applied",
            "decided_by_user",
            "agent_action_proposal",
            "agent_action_proposal__agent_run",
            "agent_action_proposal__agent_run__agent",
        ).prefetch_related("approvals", "executions", "audit_entries")

        queryset = self._apply_company_scope(queryset)

        agent_slug = self.request.query_params.get("agent")
        if agent_slug:
            queryset = queryset.filter(
                agent_action_proposal__agent_run__agent__slug=agent_slug
            )

        return queryset

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request, *args, **kwargs):
        self.permission_action = "view"

        queryset = self.filter_queryset(
            self.get_queryset().filter(
                decision_status=AgentDecision.DecisionStatus.AWAITING_APPROVAL
            )
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        self.permission_action = "approve"

        decision = self.get_object()
        serializer = DecisionApprovalCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DecisionOrchestrator.approve_decision(
            decision=decision,
            approved_by=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )

        decision.refresh_from_db()
        return Response(self.get_serializer(decision).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        self.permission_action = "approve"

        decision = self.get_object()
        serializer = DecisionApprovalCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DecisionOrchestrator.reject_decision(
            decision=decision,
            rejected_by=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )

        decision.refresh_from_db()
        return Response(self.get_serializer(decision).data)

    @action(detail=True, methods=["post"])
    def reexecute(self, request, pk=None):
        self.permission_action = "manage"

        decision = self.get_object()
        execution = DecisionOrchestrator.reexecute_decision(
            decision=decision,
            requested_by=request.user
        )

        return Response(DecisionExecutionSerializer(execution).data)


class DecisionExecutionViewSet(ScopedDecisionMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DecisionExecutionSerializer
    permission_classes = [AIDecisionPermission]
    lookup_field = "public_id"

    filterset_fields = ("execution_status", "executed_by_mode")
    search_fields = ("execution_summary", "error_message")
    ordering_fields = ("created_at", "executed_at", "finished_at", "duration_ms")

    def get_queryset(self):
        queryset = DecisionExecution.objects.select_related(
            "decision",
            "executed_by_user",
            "decision__company",
            "decision__site",
        )
        return self._apply_company_scope(queryset)