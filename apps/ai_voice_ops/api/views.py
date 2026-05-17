from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_voice_ops.api.serializers import (
    VoiceCatalogSerializer,
    VoiceInteractionSerializer,
    VoiceOpsProfileSerializer,
    VoiceProcessRequestSerializer,
)
from apps.ai_voice_ops.models import VoiceInteraction, VoiceOpsProfile
from apps.ai_voice_ops.services.orchestrator import VoiceOpsOrchestrator
from apps.companies.models import Membership


class VoiceOpsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = None
        company_id = request.query_params.get("company") or request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        domain_slug = "ai_agents_admin"
        action_slug = getattr(view, "permission_action", "view")
        persona = request.data.get("persona") if hasattr(request, "data") else None
        if persona == "technician":
            domain_slug = "work_execution"
            action_slug = "execute"
        elif persona == "client":
            domain_slug = "client_portal_dashboard"
            action_slug = "view"
        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug=domain_slug,
            action_slug=action_slug,
            company=company,
            module_name="ai_voice_ops",
            resource_type="ai_voice_ops_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed or request.user.is_staff


class ScopedVoiceMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_scope(self, queryset, *, company_field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{company_field}__in": company_ids}) | Q(**{f"{company_field}__isnull": True}))


class VoiceInteractionViewSet(ScopedVoiceMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = VoiceInteractionSerializer
    permission_classes = [VoiceOpsPermission]
    lookup_field = "public_id"
    filterset_fields = ("persona", "channel", "transcript_status", "action_status", "company", "site")
    search_fields = ("transcript_text", "detected_intent")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = VoiceInteraction.objects.select_related("user", "company", "site")
        return self._apply_scope(queryset)


class VoiceOpsProfileViewSet(ScopedVoiceMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = VoiceOpsProfileSerializer
    permission_classes = [VoiceOpsPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_scope(VoiceOpsProfile.objects.select_related("company"))


class VoiceProcessView(APIView):
    permission_classes = [VoiceOpsPermission]

    def post(self, request, *args, **kwargs):
        serializer = VoiceProcessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = VoiceOpsOrchestrator.process(
                request=request,
                persona=serializer.validated_data["persona"],
                channel=serializer.validated_data["channel"],
                input_mode=serializer.validated_data["input_mode"],
                locale=serializer.validated_data["locale"],
                transcript_text=serializer.validated_data.get("transcript_text", ""),
                audio_metadata=serializer.validated_data.get("audio_metadata", {}),
                context_seed=serializer.validated_data.get("context_seed", {}),
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        return Response(
            {
                "interaction": VoiceInteractionSerializer(payload["interaction"]).data,
                "intent": payload["intent"],
                "context": payload["context"],
                "response": payload["response"],
                "action": payload["action"],
            }
        )


class VoiceCatalogView(APIView):
    permission_classes = [VoiceOpsPermission]

    def get(self, request, *args, **kwargs):
        return Response(VoiceCatalogSerializer.build_catalog())
