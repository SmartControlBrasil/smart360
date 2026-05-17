from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_autonomous_ops.api.serializers import (
    AutonomousExecutionGuardSerializer,
    AutonomousExecutionSerializer,
    AutonomousIncidentSerializer,
    AutonomousModeConfigSerializer,
)
from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousExecutionGuard, AutonomousIncident, AutonomousModeConfig
from apps.ai_autonomous_ops.services.health import AutonomousHealthService
from apps.companies.models import Membership
from apps.observability_center.services.observability_service import SystemEventService


class AutonomousPermission(permissions.BasePermission):
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
            module_name="ai_autonomous_ops",
            resource_type="ai_autonomous_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{field}__in": company_ids}) | Q(**{f"{field}__isnull": True}))


class AutonomousModeConfigViewSet(ScopedMixin, viewsets.ModelViewSet):
    serializer_class = AutonomousModeConfigSerializer
    permission_classes = [AutonomousPermission]
    permission_action = "manage"
    lookup_field = "public_id"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return self._apply_company_scope(AutonomousModeConfig.objects.all())

    @action(detail=True, methods=["post"])
    def kill_switch(self, request, *args, **kwargs):
        config = self.get_object()
        config.kill_switch_enabled = bool(request.data.get("enabled", True))
        config.save(update_fields=["kill_switch_enabled", "updated_at"])
        SystemEventService.log_system_event(
            event_type="autonomy.kill_switch.activated",
            source_module="ai_autonomous_ops",
            message="Kill switch de autonomia atualizado.",
            entity_type="autonomous_mode_config",
            entity_id=str(config.public_id),
            user=request.user,
            company=config.company,
            payload={"enabled": config.kill_switch_enabled},
        )
        return Response(self.get_serializer(config).data, status=status.HTTP_200_OK)


class AutonomousExecutionViewSet(ScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AutonomousExecutionSerializer
    permission_classes = [AutonomousPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_company_scope(
            AutonomousExecution.objects.select_related("company", "site", "source_decision", "source_simulation").prefetch_related("incidents", "audit_entries")
        )

    @action(detail=True, methods=["post"])
    def rollback(self, request, *args, **kwargs):
        from apps.ai_autonomous_ops.services.orchestrator import AutonomousOperationsService

        execution = self.get_object()
        AutonomousOperationsService.rollback(autonomous_execution=execution, requested_by=request.user)
        execution.refresh_from_db()
        return Response(self.get_serializer(execution).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def health(self, request, *args, **kwargs):
        company = None
        company_id = request.query_params.get("company")
        if company_id:
            company = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = company.company if company else None
        payload = AutonomousHealthService.summary(company=company)
        return Response(
            {
                **payload,
                "recent_incidents": AutonomousIncidentSerializer(payload["recent_incidents"], many=True).data,
            }
        )


class AutonomousIncidentViewSet(ScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AutonomousIncidentSerializer
    permission_classes = [AutonomousPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_company_scope(AutonomousIncident.objects.select_related("company", "site", "autonomous_execution"))


class AutonomousExecutionGuardViewSet(ScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AutonomousExecutionGuardSerializer
    permission_classes = [AutonomousPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_company_scope(AutonomousExecutionGuard.objects.all())
