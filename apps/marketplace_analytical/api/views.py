from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    AnalyticalAssignment,
    AnalyticalMatchingRecord,
    AnalyticalProvider,
    AnalyticalReport,
    AnalyticalRequest,
    AnalyticalReview,
    AnalyticalService,
    AnalyticalServiceCapability,
    AnalyticalServiceCategory,
    AnalyticalServiceRegion,
)
from ..services.analytical_service import AnalyticalAssignmentService
from .serializers import (
    AnalyticalAssignmentSerializer,
    AnalyticalMatchingRecordSerializer,
    AnalyticalProviderSerializer,
    AnalyticalReportSerializer,
    AnalyticalRequestSerializer,
    AnalyticalReviewSerializer,
    AnalyticalServiceCapabilitySerializer,
    AnalyticalServiceCategorySerializer,
    AnalyticalServiceRegionSerializer,
    AnalyticalServiceSerializer,
)


class MarketplaceAnalyticalBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class AnalyticalProviderViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalProvider.objects.select_related("company", "user").all()
    serializer_class = AnalyticalProviderSerializer
    filterset_fields = ("provider_type", "verification_status", "marketplace_status", "is_active")
    search_fields = ("display_name", "legal_name", "document_number", "contact_email")
    ordering_fields = ("display_name", "rating_average", "completed_jobs_count", "updated_at")


class AnalyticalServiceCategoryViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalServiceCategory.objects.all()
    serializer_class = AnalyticalServiceCategorySerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class AnalyticalServiceViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalService.objects.select_related("provider", "category").prefetch_related("capabilities", "service_regions").all()
    serializer_class = AnalyticalServiceSerializer
    filterset_fields = ("provider", "category", "service_type", "delivery_type", "price_model", "is_active")
    search_fields = ("title", "description", "provider__display_name", "category__name")
    ordering_fields = ("title", "estimated_turnaround_days", "updated_at")


class AnalyticalServiceCapabilityViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalServiceCapability.objects.select_related("analytical_service").all()
    serializer_class = AnalyticalServiceCapabilitySerializer
    filterset_fields = ("analytical_service",)
    search_fields = ("capability_name", "description", "notes")
    ordering_fields = ("created_at", "updated_at")


class AnalyticalServiceRegionViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalServiceRegion.objects.select_related("analytical_service").all()
    serializer_class = AnalyticalServiceRegionSerializer
    filterset_fields = ("analytical_service", "state", "country", "coverage_type")
    search_fields = ("region_name", "state", "country")
    ordering_fields = ("region_name", "updated_at")


class AnalyticalRequestViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalRequest.objects.select_related(
        "requester_user",
        "requester_company",
        "category",
        "related_asset",
        "related_site",
        "related_service_order",
    ).all()
    serializer_class = AnalyticalRequestSerializer
    filterset_fields = ("category", "priority", "status", "origin", "state", "country")
    search_fields = ("title", "description", "city", "state")
    ordering_fields = ("requested_date", "updated_at")


class AnalyticalMatchingRecordViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalMatchingRecord.objects.select_related("analytical_request", "provider").all()
    serializer_class = AnalyticalMatchingRecordSerializer
    filterset_fields = ("analytical_request", "provider", "status")
    search_fields = ("analytical_request__title", "provider__display_name", "match_reason")
    ordering_fields = ("match_score", "created_at", "updated_at")


class AnalyticalAssignmentViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalAssignment.objects.select_related("analytical_request", "provider").all()
    serializer_class = AnalyticalAssignmentSerializer
    filterset_fields = ("analytical_request", "provider", "status")
    search_fields = ("analytical_request__title", "provider__display_name", "notes")
    ordering_fields = ("assigned_at", "updated_at")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = self.get_object()
        AnalyticalAssignmentService.transition_status(assignment=assignment, status=AnalyticalAssignment.Status.ACCEPTED)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        assignment = self.get_object()
        AnalyticalAssignmentService.transition_status(assignment=assignment, status=AnalyticalAssignment.Status.DECLINED)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        assignment = self.get_object()
        AnalyticalAssignmentService.transition_status(assignment=assignment, status=AnalyticalAssignment.Status.IN_PROGRESS)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        AnalyticalAssignmentService.transition_status(assignment=assignment, status=AnalyticalAssignment.Status.COMPLETED)
        return Response(self.get_serializer(assignment).data)


class AnalyticalReportViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalReport.objects.select_related("analytical_assignment").all()
    serializer_class = AnalyticalReportSerializer
    filterset_fields = ("analytical_assignment",)
    search_fields = ("title", "summary", "technical_conclusion", "recommendations")
    ordering_fields = ("created_at", "updated_at")


class AnalyticalReviewViewSet(MarketplaceAnalyticalBaseViewSet):
    queryset = AnalyticalReview.objects.select_related("analytical_assignment", "reviewer_user", "reviewer_company").all()
    serializer_class = AnalyticalReviewSerializer
    filterset_fields = ("analytical_assignment", "rating")
    search_fields = ("comment",)
    ordering_fields = ("created_at", "updated_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        output = AnalyticalReviewSerializer(review, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
