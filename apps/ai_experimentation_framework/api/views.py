from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_experimentation_framework.api.serializers import (
    AssignmentRequestSerializer,
    ExperimentAssignmentSerializer,
    ExperimentCreateSerializer,
    ExperimentMetricSerializer,
    ExperimentSerializer,
    MetricRecordSerializer,
)
from apps.ai_experimentation_framework.models import Experiment, ExperimentAssignment
from apps.ai_experimentation_framework.services.analysis import ExperimentAnalysisService
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.companies.models import Company, Membership
from apps.smart_system.models import OperationalSite


class AIExperimentPermission(permissions.BasePermission):
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
            module_name="ai_experimentation_framework",
            resource_type="ai_experiment_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedExperimentMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, company_field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{company_field}__in": company_ids}) | Q(**{f"{company_field}__isnull": True}))


class ExperimentViewSet(ScopedExperimentMixin, viewsets.ModelViewSet):
    serializer_class = ExperimentSerializer
    permission_classes = [AIExperimentPermission]
    lookup_field = "public_id"
    filterset_fields = ("status", "target_component", "company", "site")
    search_fields = ("name", "slug", "target_reference")

    def get_queryset(self):
        queryset = Experiment.objects.select_related("company", "site", "winner_variant", "result").prefetch_related("variants").order_by("-created_at")
        return self._apply_company_scope(queryset)

    def create(self, request, *args, **kwargs):
        serializer = ExperimentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = Company.objects.filter(id=serializer.validated_data.get("company")).first() if serializer.validated_data.get("company") else None
        site = OperationalSite.objects.filter(id=serializer.validated_data.get("site")).first() if serializer.validated_data.get("site") else None
        experiment = ExperimentationEngine.create_experiment(
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            target_component=serializer.validated_data["target_component"],
            target_reference=serializer.validated_data.get("target_reference", ""),
            company=company,
            site=site,
            created_by_user=request.user,
            variants=serializer.validated_data["variants"],
            assignment_strategy=serializer.validated_data["assignment_strategy"],
            primary_metric=serializer.validated_data["primary_metric"],
            success_direction=serializer.validated_data["success_direction"],
            min_sample_size=serializer.validated_data["min_sample_size"],
            min_runtime_hours=serializer.validated_data["min_runtime_hours"],
            auto_promote=serializer.validated_data["auto_promote"],
            configuration_payload=serializer.validated_data.get("configuration_payload", {}),
        )
        return Response(self.get_serializer(experiment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, *args, **kwargs):
        experiment = self.get_object()
        serializer = AssignmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = ExperimentationEngine.resolve_assignment(
            target_component=experiment.target_component,
            target_reference=experiment.target_reference,
            entity_key=serializer.validated_data["entity_key"],
            entity_type=serializer.validated_data.get("entity_type", ""),
            company=experiment.company,
            site=experiment.site,
            context=serializer.validated_data.get("context", {}),
        )
        return Response(ExperimentAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def complete(self, request, *args, **kwargs):
        experiment = self.get_object()
        experiment = ExperimentationEngine.complete_experiment(experiment=experiment, actor_user=request.user)
        return Response(self.get_serializer(experiment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def promote(self, request, *args, **kwargs):
        experiment = self.get_object()
        variant = experiment.variants.get(public_id=request.data.get("variant_public_id"))
        experiment = ExperimentationEngine.promote_variant(experiment=experiment, variant=variant, actor_user=request.user)
        return Response(self.get_serializer(experiment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def analysis(self, request, *args, **kwargs):
        experiment = self.get_object()
        result = ExperimentAnalysisService.analyze(experiment=experiment)
        return Response(
            {
                "experiment_public_id": str(experiment.public_id),
                "summary": result.summary,
                "primary_metric": result.primary_metric,
                "confidence_level": result.confidence_level,
                "recommendation": result.recommendation,
                "result_payload": result.result_payload,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def record_metric(self, request, *args, **kwargs):
        experiment = self.get_object()
        serializer = MetricRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = None
        if serializer.validated_data.get("assignment_public_id"):
            assignment = ExperimentAssignment.objects.select_related("experiment", "variant").get(
                public_id=serializer.validated_data["assignment_public_id"],
                experiment=experiment,
            )
        metric = ExperimentationEngine.record_assignment_metric(
            assignment=assignment,
            metric_type=serializer.validated_data["metric_type"],
            value=serializer.validated_data["value"],
            unit=serializer.validated_data.get("unit", ""),
            source_component=serializer.validated_data.get("source_component", ""),
            source_reference=serializer.validated_data.get("source_reference", ""),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(ExperimentMetricSerializer(metric).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def metrics(self, request, *args, **kwargs):
        experiment = self.get_object()
        queryset = experiment.metrics.select_related("variant").order_by("-recorded_at")[:100]
        return Response(ExperimentMetricSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class ExperimentAssignmentViewSet(ScopedExperimentMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ExperimentAssignmentSerializer
    permission_classes = [AIExperimentPermission]
    lookup_field = "public_id"
    filterset_fields = ("experiment", "variant", "company", "site", "entity_type")

    def get_queryset(self):
        queryset = ExperimentAssignment.objects.select_related("experiment", "variant", "company", "site").order_by("-assigned_at")
        return self._apply_company_scope(queryset)

