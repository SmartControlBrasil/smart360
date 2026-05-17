from django.shortcuts import get_object_or_404
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
