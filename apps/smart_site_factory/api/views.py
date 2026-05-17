from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shared_kernel.api_docs.responses import common_error_responses

from ..models import (
    ConfiguratorOption,
    ConfiguratorQuestion,
    DeliveryRecord,
    Niche,
    ProductionTask,
    SiteOrder,
    SiteProjectIntake,
    Template,
    TemplateRecommendationRule,
)
from ..services.order_service import ProductionService
from .serializers import (
    ConfiguratorOptionSerializer,
    ConfiguratorQuestionSerializer,
    DeliveryRecordSerializer,
    NicheSerializer,
    ProductionTaskSerializer,
    SiteOrderCreateSerializer,
    SiteOrderSerializer,
    SiteProjectIntakeSerializer,
    TemplateRecommendationRuleSerializer,
    TemplateSerializer,
)


class BaseSSFModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


@extend_schema_view(
    list=extend_schema(
        tags=["Smart Site Factory"],
        summary="Listar nichos",
        description="Lista nichos disponiveis para montagem de sites.",
        responses={200: NicheSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Smart Site Factory"],
        summary="Criar nicho",
        description="Cria um novo nicho de negocio para o catalogo da Site Factory.",
        request=NicheSerializer,
        responses={201: NicheSerializer, **common_error_responses()},
    ),
)
class NicheViewSet(BaseSSFModelViewSet):
    queryset = Niche.objects.all().order_by("name")
    serializer_class = NicheSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


@extend_schema_view(
    list=extend_schema(
        tags=["Smart Site Factory"],
        summary="Listar templates",
        description="Lista templates por nicho, status e tipo.",
        responses={200: TemplateSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Smart Site Factory"],
        summary="Criar template",
        description="Cria um template comercializavel do catalogo.",
        request=TemplateSerializer,
        responses={201: TemplateSerializer, **common_error_responses()},
    ),
)
class TemplateViewSet(BaseSSFModelViewSet):
    queryset = Template.objects.select_related("niche").all().order_by("niche__name", "name")
    serializer_class = TemplateSerializer
    filterset_fields = ("niche", "status", "template_type", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "base_price", "updated_at")


class ConfiguratorQuestionViewSet(BaseSSFModelViewSet):
    queryset = ConfiguratorQuestion.objects.select_related("niche").prefetch_related("options").all()
    serializer_class = ConfiguratorQuestionSerializer
    filterset_fields = ("niche", "question_type", "is_active")
    search_fields = ("text",)
    ordering_fields = ("order", "updated_at")


class ConfiguratorOptionViewSet(BaseSSFModelViewSet):
    queryset = ConfiguratorOption.objects.select_related("question", "question__niche").all()
    serializer_class = ConfiguratorOptionSerializer
    filterset_fields = ("question", "is_active")
    search_fields = ("label", "value", "question__text")
    ordering_fields = ("order", "updated_at")


class TemplateRecommendationRuleViewSet(BaseSSFModelViewSet):
    queryset = (
        TemplateRecommendationRule.objects.select_related("niche", "question", "option", "recommended_template")
        .all()
        .order_by("priority")
    )
    serializer_class = TemplateRecommendationRuleSerializer
    filterset_fields = ("niche", "recommended_template", "is_active")
    search_fields = ("niche__name", "recommended_template__name", "notes")
    ordering_fields = ("priority", "updated_at")


@extend_schema_view(
    list=extend_schema(
        tags=["Smart Site Factory"],
        summary="Listar pedidos de site",
        description="Lista pedidos da linha de producao de sites.",
        responses={200: SiteOrderSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Smart Site Factory"],
        summary="Criar pedido de site",
        description="Cria um pedido usando nicho, respostas do configurador e template selecionado ou recomendado.",
        request=SiteOrderCreateSerializer,
        responses={201: SiteOrderSerializer, **common_error_responses()},
    ),
)
class SiteOrderViewSet(BaseSSFModelViewSet):
    queryset = (
        SiteOrder.objects.select_related("company", "requester", "niche", "selected_template", "recommended_template")
        .prefetch_related("answers__question", "answers__option", "production_tasks")
        .all()
    )
    filterset_fields = ("status", "niche", "company")
    search_fields = ("public_id", "company__name", "requester__email", "niche__name")
    ordering_fields = ("ordered_at", "final_price", "updated_at")

    def get_serializer_class(self):
        if self.action == "create":
            return SiteOrderCreateSerializer
        return SiteOrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output = SiteOrderSerializer(order, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class SiteProjectIntakeViewSet(BaseSSFModelViewSet):
    queryset = SiteProjectIntake.objects.select_related("site_order").all()
    serializer_class = SiteProjectIntakeSerializer
    filterset_fields = ("site_order", "city", "state")
    search_fields = ("company_name", "site_order__public_id")
    ordering_fields = ("created_at", "updated_at")


@extend_schema_view(
    start=extend_schema(
        tags=["Smart Site Factory"],
        summary="Iniciar tarefa de producao",
        description="Move a tarefa para o status em andamento.",
        responses={200: ProductionTaskSerializer, **common_error_responses(include_not_found=True)},
    ),
    complete=extend_schema(
        tags=["Smart Site Factory"],
        summary="Concluir tarefa de producao",
        description="Marca a tarefa como concluida no fluxo de producao.",
        responses={200: ProductionTaskSerializer, **common_error_responses(include_not_found=True)},
    ),
)
class ProductionTaskViewSet(BaseSSFModelViewSet):
    queryset = ProductionTask.objects.select_related("site_order", "assignee").all()
    serializer_class = ProductionTaskSerializer
    filterset_fields = ("site_order", "stage", "status", "assignee")
    search_fields = ("site_order__public_id", "assignee__email", "notes")
    ordering_fields = ("due_date", "order", "updated_at")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        task = self.get_object()
        ProductionService.mark_task_status(task=task, status=ProductionTask.Status.IN_PROGRESS)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        ProductionService.mark_task_status(task=task, status=ProductionTask.Status.DONE)
        return Response(self.get_serializer(task).data)


class DeliveryRecordViewSet(BaseSSFModelViewSet):
    queryset = DeliveryRecord.objects.select_related("site_order").all()
    serializer_class = DeliveryRecordSerializer
    filterset_fields = ("site_order", "acceptance_status")
    search_fields = ("site_order__public_id", "delivered_url")
    ordering_fields = ("delivered_at", "updated_at")
