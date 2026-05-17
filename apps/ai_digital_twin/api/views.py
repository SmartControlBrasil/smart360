from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_digital_twin.api.serializers import (
    DigitalTwinSerializer,
    DigitalTwinSignalSerializer,
    DigitalTwinSnapshotSerializer,
)
from apps.ai_digital_twin.models import DigitalTwin, DigitalTwinSignal, DigitalTwinSnapshot
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.companies.models import Membership


class DigitalTwinPermission(permissions.BasePermission):
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
            action_slug=getattr(view, "permission_action", "view"),
            company=company,
            module_name="ai_digital_twin",
            resource_type="ai_digital_twin_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedTwinMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_scope(self, queryset, *, company_field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{company_field}__in": company_ids}) | Q(**{f"{company_field}__isnull": True}))


class DigitalTwinViewSet(ScopedTwinMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DigitalTwinSerializer
    permission_classes = [DigitalTwinPermission]
    lookup_field = "public_id"
    filterset_fields = ("twin_type", "risk_level", "status", "company", "site")
    search_fields = ("current_state_summary", "external_reference", "site__name", "asset__name", "asset__asset_tag")
    ordering_fields = ("last_projected_at", "updated_at", "created_at")

    def get_queryset(self):
        queryset = DigitalTwin.objects.select_related("company", "site", "asset", "asset__category", "contract").prefetch_related("signals", "projections")
        return self._apply_scope(queryset)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        DigitalTwinOrchestrator.view(digital_twin=self.get_object(), user=request.user)
        return response

    @action(detail=False, methods=["get"], url_path="by-site/(?P<site_public_id>[^/.]+)")
    def by_site(self, request, site_public_id=None):
        twin = self.get_queryset().filter(site__public_id=site_public_id, twin_type=DigitalTwin.TwinType.SITE_OPERATIONAL).first()
        if twin is None:
            return Response({"detail": "Twin nao encontrado."}, status=404)
        DigitalTwinOrchestrator.view(digital_twin=twin, user=request.user)
        return Response(self.get_serializer(twin).data)

    @action(detail=False, methods=["get"], url_path="by-asset/(?P<asset_public_id>[^/.]+)")
    def by_asset(self, request, asset_public_id=None):
        twin = self.get_queryset().filter(asset__public_id=asset_public_id, twin_type=DigitalTwin.TwinType.ASSET_OPERATIONAL).first()
        if twin is None:
            return Response({"detail": "Twin nao encontrado."}, status=404)
        DigitalTwinOrchestrator.view(digital_twin=twin, user=request.user)
        return Response(self.get_serializer(twin).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, *args, **kwargs):
        twin = self.get_object()
        return Response(
            {
                "public_id": str(twin.public_id),
                "twin_type": twin.twin_type,
                "status": twin.status,
                "risk_level": twin.risk_level,
                "current_state_summary": twin.current_state_summary,
                "summary_payload": twin.summary_payload,
            }
        )

    @action(detail=True, methods=["get"])
    def timeline(self, request, *args, **kwargs):
        twin = self.get_object()
        return Response({"items": twin.timeline_payload})

    @action(detail=True, methods=["get"], url_path="active-signals")
    def active_signals(self, request, *args, **kwargs):
        twin = self.get_object()
        queryset = twin.signals.filter(is_active=True).order_by("-occurred_at")
        return Response(DigitalTwinSignalSerializer(queryset, many=True).data)

    @action(detail=True, methods=["get"], url_path="risk-profile")
    def risk_profile(self, request, *args, **kwargs):
        twin = self.get_object()
        return Response(twin.risk_payload)

    @action(detail=True, methods=["get"])
    def snapshots(self, request, *args, **kwargs):
        twin = self.get_object()
        queryset = twin.snapshots.order_by("-snapshot_time")[:20]
        return Response(DigitalTwinSnapshotSerializer(queryset, many=True).data)


class DigitalTwinSignalViewSet(ScopedTwinMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DigitalTwinSignalSerializer
    permission_classes = [DigitalTwinPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_scope(DigitalTwinSignal.objects.select_related("digital_twin", "digital_twin__company"), company_field="digital_twin__company_id")


class DigitalTwinSnapshotViewSet(ScopedTwinMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DigitalTwinSnapshotSerializer
    permission_classes = [DigitalTwinPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_scope(DigitalTwinSnapshot.objects.select_related("digital_twin", "digital_twin__company"), company_field="digital_twin__company_id")

