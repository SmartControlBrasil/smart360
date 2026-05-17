from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.api.serializers import (
    AccessAuditLogSerializer,
    AccessPolicySerializer,
    EffectivePermissionSerializer,
    MyRolesSerializer,
    PermissionActionSerializer,
    PermissionCheckSerializer,
    PermissionDomainSerializer,
    PolicyAssignmentSerializer,
    PolicyEvaluationSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    SensitiveActionApprovalSerializer,
    UserRoleAssignmentSerializer,
)
from apps.access_control_center.models import (
    AccessAuditLog,
    AccessPolicy,
    PermissionAction,
    PermissionDomain,
    PolicyAssignment,
    Role,
    RolePermission,
    SensitiveActionApproval,
    UserRoleAssignment,
)
from apps.access_control_center.services.access_service import (
    AccessControlService,
    PolicyEvaluationService,
    SensitiveActionApprovalService,
)
from shared_kernel.api_docs.responses import common_error_responses


@extend_schema_view(
    list=extend_schema(
        tags=["Access Control"],
        summary="Listar dominios de permissao",
        description="Lista os dominios funcionais usados no RBAC do ecossistema.",
        responses={200: PermissionDomainSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Access Control"],
        summary="Criar dominio de permissao",
        description="Cria um dominio funcional para agrupamento de acoes controladas por RBAC.",
        request=PermissionDomainSerializer,
        responses={201: PermissionDomainSerializer, **common_error_responses()},
    ),
)
class PermissionDomainViewSet(viewsets.ModelViewSet):
    queryset = PermissionDomain.objects.all()
    serializer_class = PermissionDomainSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["module_name", "is_active"]
    search_fields = ["name", "slug", "description", "module_name"]
    ordering_fields = ["module_name", "name", "created_at"]


class PermissionActionViewSet(viewsets.ModelViewSet):
    queryset = PermissionAction.objects.select_related("domain").all()
    serializer_class = PermissionActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["domain", "is_active"]
    search_fields = ["action_name", "slug", "description", "domain__name", "domain__module_name"]
    ordering_fields = ["domain__module_name", "action_name", "created_at"]


@extend_schema_view(
    list=extend_schema(
        tags=["Access Control"],
        summary="Listar roles",
        description="Lista roles do modulo de governanca de acesso.",
        responses={200: RoleSerializer, **common_error_responses()},
    ),
    create=extend_schema(
        tags=["Access Control"],
        summary="Criar role",
        description="Cria um papel reutilizavel no sistema de RBAC.",
        request=RoleSerializer,
        responses={201: RoleSerializer, **common_error_responses()},
    ),
)
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["role_type", "is_system_role", "is_active"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["name", "updated_at", "created_at"]


class RolePermissionViewSet(viewsets.ModelViewSet):
    queryset = RolePermission.objects.select_related("role", "permission_domain", "permission_action").all()
    serializer_class = RolePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["role", "permission_domain", "permission_action", "is_allowed"]
    search_fields = ["role__name", "permission_domain__name", "permission_action__action_name"]
    ordering_fields = ["created_at", "role__name"]


class UserRoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = UserRoleAssignment.objects.select_related("user", "role", "company", "assigned_by").all()
    serializer_class = UserRoleAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["user", "role", "company", "scope_type", "is_active"]
    search_fields = ["user__email", "role__name", "company__name", "scope_reference"]
    ordering_fields = ["assigned_at", "expires_at", "updated_at"]

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class AccessPolicyViewSet(viewsets.ModelViewSet):
    queryset = AccessPolicy.objects.select_related("domain").all()
    serializer_class = AccessPolicySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["domain", "policy_type", "is_active"]
    search_fields = ["name", "slug", "domain__name"]
    ordering_fields = ["name", "created_at"]


class PolicyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = PolicyAssignment.objects.select_related("policy", "role", "user", "company").all()
    serializer_class = PolicyAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["policy", "role", "user", "company", "is_active"]
    search_fields = ["policy__name", "role__name", "user__email", "company__name"]
    ordering_fields = ["assigned_at", "created_at"]


class AccessAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccessAuditLog.objects.select_related("user").all()
    serializer_class = AccessAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["user", "action", "domain", "decision"]
    search_fields = ["user__email", "action", "domain", "reason", "resource_type", "resource_id"]
    ordering_fields = ["created_at"]


@extend_schema_view(
    approve=extend_schema(
        tags=["Access Control"],
        summary="Aprovar acao sensivel",
        description="Aprova uma solicitacao de acao sensivel registrada no modulo.",
        responses={200: SensitiveActionApprovalSerializer, **common_error_responses(include_not_found=True)},
    ),
    reject=extend_schema(
        tags=["Access Control"],
        summary="Rejeitar acao sensivel",
        description="Rejeita uma solicitacao de acao sensivel registrada no modulo.",
        responses={200: SensitiveActionApprovalSerializer, **common_error_responses(include_not_found=True)},
    ),
)
class SensitiveActionApprovalViewSet(viewsets.ModelViewSet):
    queryset = SensitiveActionApproval.objects.select_related("domain", "requested_by", "approved_by").all()
    serializer_class = SensitiveActionApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["domain", "action_name", "status", "requested_by", "approved_by"]
    search_fields = ["action_name", "domain__name", "requested_by__email", "approved_by__email"]
    ordering_fields = ["created_at", "updated_at", "approved_at"]

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval = self.get_object()
        SensitiveActionApprovalService.approve(approval=approval, approved_by=request.user)
        return Response(self.get_serializer(approval).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval = self.get_object()
        SensitiveActionApprovalService.reject(approval=approval, approved_by=request.user)
        return Response(self.get_serializer(approval).data, status=status.HTTP_200_OK)


class CheckPermissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Access Control"],
        summary="Verificar permissao",
        description="Avalia uma permissao efetiva usando RBAC, escopo e policies aplicaveis.",
        request=PermissionCheckSerializer,
        responses={200: OpenApiResponse(description="Resultado da verificacao."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = PermissionCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        allowed, reason = AccessControlService.check_permission(
            user=request.user,
            domain_slug=data["domain_slug"],
            action_slug=data["action_slug"],
            company=data.get("company"),
            module_name=data.get("module_name", ""),
            resource_type=data.get("resource_type", ""),
            resource_id=data.get("resource_id", ""),
            context=data.get("context", {}),
        )
        return Response({"allowed": allowed, "reason": reason}, status=status.HTTP_200_OK)


class MyRolesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Access Control"],
        summary="Minhas roles",
        description="Lista as atribuicoes de role do usuario autenticado.",
        responses={200: MyRolesSerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        assignments = UserRoleAssignment.objects.select_related("role", "company").filter(user=request.user)
        serializer = MyRolesSerializer(assignments, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data}, status=status.HTTP_200_OK)


class MyPermissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Access Control"],
        summary="Minhas permissoes",
        description="Lista permissoes efetivas agregadas a partir das roles atuais do usuario.",
        responses={200: EffectivePermissionSerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        module_name = request.query_params.get("module_name", "")
        permissions_data = AccessControlService.get_user_permissions(request.user, module_name=module_name)
        serializer = EffectivePermissionSerializer(permissions_data, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data}, status=status.HTTP_200_OK)


class PolicyEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Access Control"],
        summary="Avaliar policy",
        description="Executa avaliacao pontual de uma policy com contexto informado.",
        request=PolicyEvaluationSerializer,
        responses={200: OpenApiResponse(description="Resultado da avaliacao da policy."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = PolicyEvaluationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = serializer.validated_data["policy"]
        company = serializer.validated_data.get("company")
        context = serializer.validated_data.get("context", {})
        allowed, reason = PolicyEvaluationService.evaluate_policy(
            policy,
            user=request.user,
            company=company,
            context=context,
        )
        return Response(
            {
                "allowed": allowed,
                "reason": reason,
                "policy": AccessPolicySerializer(policy).data,
            },
            status=status.HTTP_200_OK,
        )
