from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.observability_center.services.observability_service import HealthcheckService

from .serializers import ApiRootSerializer, HealthCheckDetailsSerializer, HealthCheckSerializer


class HealthLiveView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Observability"],
        summary="Liveness probe",
        description="Valida que o processo web esta respondendo e apto a receber trafego.",
        responses={200: HealthCheckSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = HealthCheckSerializer(HealthcheckService.liveness())
        return Response(serializer.data)


class HealthReadyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Observability"],
        summary="Readiness probe",
        description="Valida dependencias criticas para operacao da aplicacao.",
        responses={200: HealthCheckDetailsSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = HealthCheckDetailsSerializer(HealthcheckService.readiness())
        return Response(serializer.data)


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Core Platform"],
        summary="Healthcheck da plataforma",
        description="Retorna um resumo tecnico da disponibilidade da API e dos componentes centrais.",
        responses={200: HealthCheckSerializer},
    )
    def get(self, request, *args, **kwargs):
        summary = HealthcheckService.summary()
        payload = {key: summary[key] for key in ("status", "service", "environment", "version")}
        serializer = HealthCheckSerializer(payload)
        return Response(serializer.data)


class HealthCheckDetailsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Observability"],
        summary="Healthcheck detalhado",
        description="Retorna o estado detalhado de banco, cache e configuracao celery do ecossistema.",
        responses={200: HealthCheckDetailsSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = HealthCheckDetailsSerializer(HealthcheckService.summary())
        return Response(serializer.data)


class ApiRootView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Core Platform"],
        summary="API root",
        description="Apresenta a visao resumida da API, versao atual, modulos registrados e metodos de autenticacao.",
        responses={200: ApiRootSerializer, 401: OpenApiResponse(description="Nao autenticado.")},
    )
    def get(self, request, *args, **kwargs):
        payload = {
            "name": "SMART360 API",
            "version": "v1",
            "modules": list(settings.INTERNAL_MODULES.keys()),
            "authentication": ["basic", "session", "token"],
        }
        serializer = ApiRootSerializer(payload)
        return Response(serializer.data)
