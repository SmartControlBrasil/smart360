from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from ..models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianAvailability,
    TechnicianCompensationRecord,
    TechnicianMatchingRecord,
    TechnicianPortfolioItem,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
    TechnicianWorkReport,
)
from ..services.access import MarketplaceAccessService
from ..services.marketplace_service import TechnicianServiceRequestService
from ..services.marketplace_service import (
    TechnicianAssignmentService,
    TechnicianMatchingService,
    TechnicianServiceOfferService,
)
from apps.ai_agents_center.services.marketplace_triggers import MarketplaceAllocationTriggerService
from .serializers import (
    ServiceRegionSerializer,
    TechnicianAssignmentSerializer,
    TechnicianAvailabilitySerializer,
    TechnicianCompensationRecordSerializer,
    TechnicianMatchingRecordSerializer,
    TechnicianPortfolioItemSerializer,
    TechnicianProfileSerializer,
    TechnicianReviewSerializer,
    TechnicianServiceOfferSerializer,
    TechnicianServiceRegionSerializer,
    TechnicianServiceRequestSerializer,
    TechnicianSkillAssignmentSerializer,
    TechnicianSkillSerializer,
    TechnicianWorkReportSerializer,
)


class MarketplaceTechniciansBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class TechnicianProfileViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianProfile.objects.select_related("user").all()
    serializer_class = TechnicianProfileSerializer
    filterset_fields = ("profile_type", "verification_status", "marketplace_status", "is_active")
    search_fields = ("display_name", "user__email", "document_number", "phone", "whatsapp")
    ordering_fields = ("display_name", "rating_average", "completed_jobs_count", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_profiles_queryset(self.request.user, super().get_queryset())


class TechnicianSkillViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianSkill.objects.all()
    serializer_class = TechnicianSkillSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class TechnicianSkillAssignmentViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianSkillAssignment.objects.select_related("technician_profile", "skill").all()
    serializer_class = TechnicianSkillAssignmentSerializer
    filterset_fields = ("technician_profile", "skill", "proficiency_level")
    search_fields = ("technician_profile__display_name", "skill__name", "notes")
    ordering_fields = ("created_at", "updated_at")


class ServiceRegionViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = ServiceRegion.objects.all()
    serializer_class = ServiceRegionSerializer
    filterset_fields = ("state", "city", "region_type", "is_active")
    search_fields = ("name", "state", "city")
    ordering_fields = ("name", "updated_at")


class TechnicianServiceRegionViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianServiceRegion.objects.select_related("technician_profile", "service_region").all()
    serializer_class = TechnicianServiceRegionSerializer
    filterset_fields = ("technician_profile", "service_region", "coverage_type")
    search_fields = ("technician_profile__display_name", "service_region__name")
    ordering_fields = ("created_at", "updated_at")


class TechnicianAvailabilityViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianAvailability.objects.select_related("technician_profile").all()
    serializer_class = TechnicianAvailabilitySerializer
    filterset_fields = ("technician_profile", "weekday", "is_available")
    search_fields = ("technician_profile__display_name", "notes")
    ordering_fields = ("weekday", "start_time", "updated_at")


class TechnicianPortfolioItemViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianPortfolioItem.objects.select_related("technician_profile").all()
    serializer_class = TechnicianPortfolioItemSerializer
    filterset_fields = ("technician_profile", "is_active")
    search_fields = ("title", "description", "technician_profile__display_name")
    ordering_fields = ("ordering", "updated_at")


class TechnicianServiceRequestViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianServiceRequest.objects.select_related(
        "requester_user",
        "requester_company",
        "related_client",
        "related_site",
        "related_asset",
        "related_service_order",
    ).all()
    serializer_class = TechnicianServiceRequestSerializer
    filterset_fields = ("service_type", "priority", "status", "origin", "state", "city")
    search_fields = ("title", "description", "city", "state")
    ordering_fields = ("requested_date", "created_at", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_requests_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        if not MarketplaceAccessService.is_company_operator(self.request.user):
            raise PermissionDenied("Only company users can create service requests.")
        service_request = TechnicianServiceRequestService.create_request(user=self.request.user, validated_data=serializer.validated_data)
        serializer.instance = service_request

    @action(detail=True, methods=["get", "post"])
    def matching(self, request, pk=None):
        service_request = self.get_object()
        if request.method.lower() == "post":
            if not MarketplaceAccessService.can_manage_request(request.user, service_request):
                raise PermissionDenied("Only company operators in scope can refresh matching.")
            TechnicianMatchingService.refresh_matches(service_request=service_request)
            try:
                MarketplaceAllocationTriggerService.run_for_request(service_request=service_request, user=request.user)
            except Exception:
                pass
        queryset = MarketplaceAccessService.scope_matching_queryset(
            request.user,
            service_request.matching_records.select_related("technician_profile", "technician_profile__user"),
        ).order_by("ranking_position", "-match_score")
        serializer = TechnicianMatchingRecordSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class TechnicianServiceOfferViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianServiceOffer.objects.select_related("service_request", "technician_profile").all()
    serializer_class = TechnicianServiceOfferSerializer
    filterset_fields = ("service_request", "technician_profile", "status")
    search_fields = ("service_request__title", "technician_profile__display_name", "message")
    ordering_fields = ("created_at", "updated_at", "proposed_amount")

    def get_queryset(self):
        return MarketplaceAccessService.scope_offers_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        technician_profile = serializer.validated_data["technician_profile"]
        service_request = serializer.validated_data["service_request"]
        if not MarketplaceAccessService.can_offer(self.request.user, service_request, technician_profile=technician_profile):
            raise PermissionDenied("Only the technician owner can submit offers for eligible requests.")
        offer = TechnicianServiceOfferService.create_offer(user=self.request.user, validated_data=serializer.validated_data)
        serializer.instance = offer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        if not MarketplaceAccessService.can_manage_request(request.user, offer.service_request):
            raise PermissionDenied("Only company operators in scope can accept offers.")
        assignment = TechnicianServiceOfferService.accept_offer(user=request.user, offer=offer)
        return Response(TechnicianAssignmentSerializer(assignment, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        if not MarketplaceAccessService.can_manage_request(request.user, offer.service_request):
            raise PermissionDenied("Only company operators in scope can reject offers.")
        TechnicianServiceOfferService.reject_offer(user=request.user, offer=offer)
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        if getattr(request.user, "technician_profile", None) is None or offer.technician_profile_id != request.user.technician_profile.id:
            raise PermissionDenied("Only the offer owner can withdraw this offer.")
        TechnicianServiceOfferService.withdraw_offer(user=request.user, offer=offer)
        return Response(self.get_serializer(offer).data)


class TechnicianMatchingRecordViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianMatchingRecord.objects.select_related("technician_service_request", "technician_profile").all()
    serializer_class = TechnicianMatchingRecordSerializer
    filterset_fields = ("technician_service_request", "technician_profile", "status")
    search_fields = ("technician_service_request__title", "technician_profile__display_name", "match_reason")
    ordering_fields = ("match_score", "created_at", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_matching_queryset(self.request.user, super().get_queryset())


class TechnicianAssignmentViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianAssignment.objects.select_related("technician_service_request", "technician_profile").all()
    serializer_class = TechnicianAssignmentSerializer
    filterset_fields = ("technician_service_request", "technician_profile", "assignment_status")
    search_fields = ("technician_service_request__title", "technician_profile__display_name")
    ordering_fields = ("assigned_at", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_assignments_queryset(self.request.user, super().get_queryset())

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment action outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.ACCEPTED,
        )
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment action outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.DECLINED,
        )
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment action outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
        )
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment action outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.COMPLETED,
        )
        return Response(self.get_serializer(assignment).data)


class TechnicianWorkReportViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianWorkReport.objects.select_related("technician_assignment").all()
    serializer_class = TechnicianWorkReportSerializer
    filterset_fields = ("technician_assignment",)
    search_fields = ("summary", "execution_notes", "next_recommendation")
    ordering_fields = ("started_at", "ended_at", "labor_minutes", "updated_at")


class TechnicianReviewViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianReview.objects.select_related("technician_profile", "assignment", "reviewer_user", "reviewer_company").all()
    serializer_class = TechnicianReviewSerializer
    filterset_fields = ("technician_profile", "assignment", "rating", "status")
    search_fields = ("comment", "technician_profile__display_name")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_reviews_queryset(self.request.user, super().get_queryset())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not MarketplaceAccessService.can_review_assignment(request.user, serializer.validated_data["assignment"]):
            raise PermissionDenied("Only company operators in scope can review assignments.")
        review = serializer.save()
        output = TechnicianReviewSerializer(review, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class TechnicianCompensationRecordViewSet(MarketplaceTechniciansBaseViewSet):
    queryset = TechnicianCompensationRecord.objects.select_related("technician_assignment").all()
    serializer_class = TechnicianCompensationRecordSerializer
    filterset_fields = ("technician_assignment", "status")
    search_fields = ("notes",)
    ordering_fields = ("created_at", "updated_at")
