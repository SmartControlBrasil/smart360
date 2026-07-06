import json
import re
from hmac import compare_digest

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shared_kernel.api_docs.responses import common_error_responses

from apps.users.models import User

from ..models import Lead, LeadAssignment, LeadCampaign, LeadInteraction, LeadQualification, LeadSource, LeadTag
from ..services.lead_service import LeadService
from .serializers import (
    LeadAssignmentSerializer,
    LeadCampaignSerializer,
    LeadInteractionSerializer,
    LeadQualificationSerializer,
    LeadSerializer,
    LeadSourceSerializer,
    LeadTagSerializer,
    LeadWriteSerializer,
)

LIVIA_PLATFORM_SOURCE_NAME = "Lívia Platform"
LIVIA_PLATFORM_SOURCE_DESCRIPTION = "Leads recebidos via integração M2M da Lívia Platform."


def _expected_livia_token() -> str:
    return str(getattr(settings, "SMART360_LIVIA_M2M_TOKEN", "") or "").strip()


def _has_valid_livia_token(request) -> bool:
    expected_token = _expected_livia_token()
    if not expected_token:
        return False
    auth_header = str(request.headers.get("Authorization") or "").strip()
    if not auth_header.startswith("Bearer "):
        return False
    received_token = auth_header.split(" ", 1)[1].strip()
    if not received_token:
        return False
    return compare_digest(received_token, expected_token)


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _find_existing_lead(*, email: str, phone: str) -> Lead | None:
    if email:
        lead = Lead.objects.filter(email__iexact=email).order_by("-id").first()
        if lead is not None:
            return lead

    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None

    for lead in Lead.objects.filter(Q(phone__isnull=False) | Q(whatsapp__isnull=False)).order_by("-id"):
        lead_phone = _normalize_phone(lead.phone)
        lead_whatsapp = _normalize_phone(lead.whatsapp)
        if normalized_phone in {lead_phone, lead_whatsapp}:
            return lead
    return None


def _livia_source() -> LeadSource:
    return LeadSource.objects.get_or_create(
        name=LIVIA_PLATFORM_SOURCE_NAME,
        defaults={
            "source_type": LeadSource.SourceType.PARTNER,
            "description": LIVIA_PLATFORM_SOURCE_DESCRIPTION,
            "is_active": True,
        },
    )[0]


def _build_note(*, tenant_slug: str, need_summary: str, source_page: str, conversation_id: str) -> str:
    parts = [
        "Lead recebido da Lívia Platform.",
        f"Tenant: {tenant_slug}" if tenant_slug else "",
        f"need_summary: {need_summary}" if need_summary else "",
        f"source_page: {source_page}" if source_page else "",
        f"conversation_id: {conversation_id}" if conversation_id else "",
    ]
    return "\n".join(part for part in parts if part)


def _merge_metadata(existing: dict, tenant_slug: str, source_page: str, conversation_id: str) -> dict:
    metadata = dict(existing or {})
    metadata.update({"origin": "livia_platform", "tenant_slug": tenant_slug})
    if source_page:
        metadata["source_page"] = source_page
    if conversation_id:
        metadata["conversation_id"] = conversation_id
    return metadata


@csrf_exempt
@require_POST
@transaction.atomic
def ingest_livia_lead(request):
    if not _has_valid_livia_token(request):
        return JsonResponse({"success": False, "error": "Unauthorized or invalid token."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Payload JSON inválido."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"success": False, "error": "Payload deve ser um objeto JSON."}, status=400)

    tenant_slug = str(payload.get("tenant_slug") or "").strip()
    name = str(payload.get("name") or "").strip()[:150]
    company = str(payload.get("company") or "").strip()[:180]
    email = str(payload.get("email") or "").strip().lower()[:254]
    phone = str(payload.get("phone") or "").strip()[:30]
    city = str(payload.get("city") or "").strip()[:100]
    need_summary = str(payload.get("need_summary") or "").strip()
    source_page = str(payload.get("source_page") or "").strip()[:500]
    conversation_id = str(payload.get("conversation_id") or "").strip()[:120]

    if not tenant_slug:
        return JsonResponse({"success": False, "error": "tenant_slug é obrigatório."}, status=400)

    if not company:
        company = name

    if not company:
        return JsonResponse({"success": False, "error": "Informe pelo menos name ou company."}, status=400)

    source = _livia_source()
    note = _build_note(
        tenant_slug=tenant_slug,
        need_summary=need_summary,
        source_page=source_page,
        conversation_id=conversation_id,
    )
    existing = _find_existing_lead(email=email, phone=phone)

    if existing is None:
        lead = LeadService.create_lead(
            user=None,
            validated_data={
                "company_name": company,
                "contact_name": name,
                "email": email,
                "phone": phone,
                "whatsapp": phone,
                "city": city,
                "source": source,
                "status": Lead.Status.NEW,
                "notes": note,
                "metadata": _merge_metadata({}, tenant_slug, source_page, conversation_id),
            },
        )
        LeadInteraction.objects.create(
            lead=lead,
            interaction_type=LeadInteraction.InteractionType.NOTE,
            channel=LeadInteraction.Channel.OTHER,
            summary=note,
        )
        return JsonResponse({"success": True, "lead_id": lead.id, "created": True}, status=201)

    update_data = {
        "notes": f"{existing.notes}\n\n{note}".strip(),
        "metadata": _merge_metadata(existing.metadata, tenant_slug, source_page, conversation_id),
    }
    if company and not existing.company_name:
        update_data["company_name"] = company
    if name and not existing.contact_name:
        update_data["contact_name"] = name
    if email and not existing.email:
        update_data["email"] = email
    if phone and not existing.phone:
        update_data["phone"] = phone
    if phone and not existing.whatsapp:
        update_data["whatsapp"] = phone
    if city and not existing.city:
        update_data["city"] = city
    if existing.source_id is None:
        update_data["source"] = source

    lead = LeadService.update_lead(lead=existing, validated_data=update_data, user=None)
    LeadInteraction.objects.create(
        lead=lead,
        interaction_type=LeadInteraction.InteractionType.NOTE,
        channel=LeadInteraction.Channel.OTHER,
        summary=note,
    )
    return JsonResponse({"success": True, "lead_id": lead.id, "created": False}, status=200)


class GrowthBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class LeadSourceViewSet(GrowthBaseViewSet):
    queryset = LeadSource.objects.all().order_by("name")
    serializer_class = LeadSourceSerializer
    filterset_fields = ("source_type", "is_active")
    search_fields = ("name", "description")
    ordering_fields = ("name", "updated_at")


class LeadTagViewSet(GrowthBaseViewSet):
    queryset = LeadTag.objects.all().order_by("name")
    serializer_class = LeadTagSerializer
    search_fields = ("name", "slug")
    ordering_fields = ("name", "updated_at")


class LeadCampaignViewSet(GrowthBaseViewSet):
    queryset = LeadCampaign.objects.all().order_by("name")
    serializer_class = LeadCampaignSerializer
    filterset_fields = ("channel", "status")
    search_fields = ("name", "objective", "description")
    ordering_fields = ("name", "updated_at")


@extend_schema_view(
    list=extend_schema(
        tags=["Growth Engine"],
        summary="Listar leads",
        description="Lista leads com filtros por nicho, cidade, status, score e responsavel.",
        responses={200: LeadSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Growth Engine"],
        summary="Criar lead",
        description="Cria um lead e recalcula score basico quando aplicavel.",
        request=LeadWriteSerializer,
        responses={201: LeadSerializer, **common_error_responses()},
    ),
    assign=extend_schema(
        tags=["Growth Engine"],
        summary="Atribuir lead",
        description="Atribui o lead a um usuario responsavel da operacao comercial.",
        responses={200: LeadSerializer, **common_error_responses(include_not_found=True)},
    ),
)
class LeadViewSet(GrowthBaseViewSet):
    queryset = (
        Lead.objects.select_related("niche", "source", "campaign", "assigned_to", "created_by")
        .prefetch_related("tags")
        .all()
    )
    filterset_fields = ("niche", "city", "status", "score", "source", "assigned_to")
    search_fields = ("company_name", "contact_name", "email", "phone", "website")
    ordering_fields = ("score", "created_at", "updated_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        source_origin = self.request.query_params.get("source_origin") or self.request.query_params.get("origin")
        if source_origin in {"livia", "livia_assistant"}:
            queryset = queryset.filter(metadata__source="livia_assistant")
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return LeadWriteSerializer
        return LeadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        output = LeadSerializer(lead, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        output = LeadSerializer(lead, context=self.get_serializer_context())
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        lead = self.get_object()
        user = get_object_or_404(User, pk=request.data["user"])
        LeadService.assign_lead(lead=lead, user=user)
        return Response(LeadSerializer(lead, context=self.get_serializer_context()).data)


class LeadInteractionViewSet(GrowthBaseViewSet):
    queryset = LeadInteraction.objects.select_related("lead", "owner").all()
    serializer_class = LeadInteractionSerializer
    filterset_fields = ("lead", "interaction_type", "channel", "owner")
    search_fields = ("lead__company_name", "summary", "owner__email")
    ordering_fields = ("happened_at", "updated_at")


class LeadQualificationViewSet(GrowthBaseViewSet):
    queryset = LeadQualification.objects.select_related("lead").all()
    serializer_class = LeadQualificationSerializer
    filterset_fields = ("lead",)
    search_fields = ("lead__company_name", "notes")
    ordering_fields = ("calculated_score", "updated_at")


class LeadAssignmentViewSet(GrowthBaseViewSet):
    queryset = LeadAssignment.objects.select_related("lead", "user").all()
    serializer_class = LeadAssignmentSerializer
    filterset_fields = ("lead", "user", "status")
    search_fields = ("lead__company_name", "user__email")
    ordering_fields = ("assigned_at", "updated_at")
