from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_policy_studio.api.serializers import (
    PolicyEvaluateSerializer,
    PolicyEvaluationSerializer,
    PolicyRuleSerializer,
    PolicyScopeSerializer,
    PolicySerializer,
    PolicySimulationRunSerializer,
    PolicyVersionCommandSerializer,
    PolicyVersionSerializer,
)
from apps.ai_policy_studio.models import Policy, PolicyEvaluation, PolicyRule, PolicyScope, PolicySimulationRun, PolicyVersion
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.ai_policy_studio.services.simulation import PolicySimulationService
from apps.ai_policy_studio.services.versioning import PolicyVersioningService
from apps.companies.models import Membership


class AIPolicyStudioPermission(permissions.BasePermission):
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
            module_name="ai_policy_studio",
            resource_type="ai_policy_studio_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedPolicyMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, field_name="scopes__company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{field_name}__in": company_ids}) | Q(**{f"{field_name}__isnull": True})).distinct()


class PolicyViewSet(ScopedPolicyMixin, viewsets.ModelViewSet):
    serializer_class = PolicySerializer
    permission_classes = [AIPolicyStudioPermission]
    lookup_field = "public_id"
    filterset_fields = ("tenant_scope", "is_global", "status")
    search_fields = ("slug", "name", "description")
    ordering_fields = ("name", "updated_at", "version")

    def get_queryset(self):
        queryset = Policy.objects.prefetch_related("scopes", "rules", "versions")
        return self._apply_company_scope(queryset)

    def perform_create(self, serializer):
        policy = serializer.save(created_by_user=self.request.user)
        PolicyVersioningService.create_version(policy=policy, created_by_user=self.request.user, change_summary="Initial version")

    def perform_update(self, serializer):
        policy = serializer.save()
        PolicyVersioningService.create_version(policy=policy, created_by_user=self.request.user, change_summary="Policy updated")

    @action(detail=True, methods=["post"])
    def version(self, request, *args, **kwargs):
        policy = self.get_object()
        serializer = PolicyVersionCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PolicyVersioningService.create_version(
            policy=policy,
            created_by_user=request.user,
            change_summary=serializer.validated_data.get("change_summary", ""),
        )
        policy.refresh_from_db()
        return Response(self.get_serializer(policy).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def simulate(self, request, *args, **kwargs):
        policy = self.get_object()
        simulation_run = PolicySimulationService.simulate(
            policy=policy,
            company=policy.scopes.filter(company__isnull=False).first().company if policy.scopes.filter(company__isnull=False).exists() else None,
            site=policy.scopes.filter(site__isnull=False).first().site if policy.scopes.filter(site__isnull=False).exists() else None,
            created_by_user=request.user,
            input_payload=request.data,
        )
        return Response(PolicySimulationRunSerializer(simulation_run).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def evaluate(self, request, *args, **kwargs):
        serializer = PolicyEvaluateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = PolicyStudioEngine.evaluate(
            module_slug=serializer.validated_data["module_slug"],
            action_type=serializer.validated_data["action_type"],
            company=serializer.validated_data.get("company"),
            site=serializer.validated_data.get("site"),
            risk_level=serializer.validated_data.get("risk_level", "any") or "any",
            autonomy_level=serializer.validated_data.get("autonomy_level", 0),
            agent_slug=serializer.validated_data.get("agent_slug", ""),
            copilot_key=serializer.validated_data.get("copilot_key", ""),
            context=serializer.validated_data.get("context", {}),
        )
        return Response(
            {
                "policy_public_id": str(result.policy.public_id) if result.policy else "",
                "rule_public_id": str(result.rule.public_id) if result.rule else "",
                "result": result.result,
                "reason": result.reason,
                "requires_approval": result.requires_approval,
                "allowed": result.allowed,
                "approver_roles": result.approver_roles,
                "autonomy_level": result.autonomy_level,
                "matched_scope": result.matched_scope,
            },
            status=status.HTTP_200_OK,
        )


class PolicyRuleViewSet(viewsets.ModelViewSet):
    serializer_class = PolicyRuleSerializer
    permission_classes = [AIPolicyStudioPermission]
    permission_action = "manage"
    lookup_field = "public_id"
    queryset = PolicyRule.objects.select_related("policy")


class PolicyScopeViewSet(viewsets.ModelViewSet):
    serializer_class = PolicyScopeSerializer
    permission_classes = [AIPolicyStudioPermission]
    permission_action = "manage"
    lookup_field = "public_id"
    queryset = PolicyScope.objects.select_related("policy", "company", "site")


class PolicyVersionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PolicyVersionSerializer
    permission_classes = [AIPolicyStudioPermission]
    lookup_field = "public_id"
    queryset = PolicyVersion.objects.select_related("policy", "created_by_user")


class PolicyEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PolicyEvaluationSerializer
    permission_classes = [AIPolicyStudioPermission]
    lookup_field = "public_id"
    filterset_fields = ("module_slug", "action_type", "result")
    queryset = PolicyEvaluation.objects.select_related("policy", "rule", "company", "site")


class PolicySimulationRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PolicySimulationRunSerializer
    permission_classes = [AIPolicyStudioPermission]
    lookup_field = "public_id"
    queryset = PolicySimulationRun.objects.select_related("policy", "company", "site", "created_by_user")
