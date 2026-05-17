from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from shared_kernel.api_docs.examples import LOGIN_REQUEST_EXAMPLE, LOGIN_RESPONSE_EXAMPLE
from shared_kernel.api_docs.responses import common_error_responses

from apps.companies.models import Membership
from apps.users.api.serializers import UserSerializer

from ..models import AuthEventLog, CompanyInvitation, OnboardingProfile, UserSession
from ..services.identity_service import (
    AuthEventService,
    EmailVerificationService,
    IdentityAuthService,
    InvitationService,
    PasswordResetService,
    SessionService,
)
from .serializers import (
    AuthEventLogSerializer,
    AuthLoginSerializer,
    AuthTokenResponseSerializer,
    ChangePasswordSerializer,
    CompanyInvitationAcceptSerializer,
    CompanyInvitationSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    OnboardingProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSessionSerializer,
)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login por email",
        description="Autentica um usuario por email e senha e retorna token de sessao reutilizavel.",
        request=AuthLoginSerializer,
        responses={
            200: AuthTokenResponseSerializer,
            **common_error_responses(),
        },
        examples=[LOGIN_REQUEST_EXAMPLE, LOGIN_RESPONSE_EXAMPLE],
    )
    def post(self, request, *args, **kwargs):
        serializer = AuthLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, token = IdentityAuthService.login(request=request, **serializer.validated_data)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"token": token, "user": UserSerializer(user).data}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Logout",
        description="Revoga a sessao autenticada atual.",
        responses={204: OpenApiResponse(description="Sessao encerrada."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        IdentityAuthService.logout(request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh do token",
        description="Rotaciona o token da sessao autenticada atual.",
        responses={200: OpenApiResponse(description="Novo token emitido."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        session = IdentityAuthService.refresh_token(request=request)
        return Response({"token": session.token_identifier}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(
        tags=["Auth"],
        summary="Perfil autenticado",
        description="Retorna os dados do usuario autenticado.",
        responses={200: UserSerializer, **common_error_responses()},
    )
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Troca de senha",
        description="Permite que o usuario autenticado altere sua propria senha.",
        request=ChangePasswordSerializer,
        responses={204: OpenApiResponse(description="Senha alterada."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            IdentityAuthService.change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Solicitar reset de senha",
        description="Cria uma solicitacao de redefinicao de senha sem expor se o email existe.",
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(description="Solicitacao recebida."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService.request_reset(email=serializer.validated_data["email"], request=request)
        return Response({"detail": "If the account exists, a reset message was queued."}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Confirmar reset de senha",
        description="Conclui a redefinicao de senha usando token valido.",
        request=PasswordResetConfirmSerializer,
        responses={204: OpenApiResponse(description="Senha redefinida."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PasswordResetService.confirm_reset(
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailVerificationRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Solicitar verificacao de email",
        description="Gera uma solicitacao de verificacao para o email do usuario autenticado.",
        request=EmailVerificationRequestSerializer,
        responses={202: OpenApiResponse(description="Solicitacao criada."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = EmailVerificationService.request_verification(user=request.user, request=request)
        return Response({"request_id": str(verification.public_id)}, status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Confirmar verificacao de email",
        description="Confirma o email do usuario com base em token de verificacao.",
        request=EmailVerificationConfirmSerializer,
        responses={204: OpenApiResponse(description="Email verificado."), **common_error_responses()},
    )
    def post(self, request, *args, **kwargs):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            EmailVerificationService.confirm_verification(token=serializer.validated_data["token"], request=request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        tags=["Auth"],
        summary="Listar sessoes do usuario",
        description="Lista as sessoes registradas do usuario autenticado.",
        responses={200: UserSessionSerializer, **common_error_responses()},
    ),
    revoke=extend_schema(
        tags=["Auth"],
        summary="Revogar sessao",
        description="Revoga uma sessao especifica do usuario autenticado.",
        responses={200: UserSessionSerializer, **common_error_responses(include_not_found=True)},
    ),
    revoke_others=extend_schema(
        tags=["Auth"],
        summary="Revogar outras sessoes",
        description="Revoga todas as outras sessoes ativas, preservando a sessao atual.",
        responses={200: OpenApiResponse(description="Outras sessoes revogadas."), **common_error_responses()},
    ),
)
class UserSessionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        session = self.get_object()
        SessionService.revoke_session(session=session)
        AuthEventService.log(
            event_type=AuthEventLog.EventType.SESSION_REVOKED,
            user=request.user,
            request=request,
            metadata={"session_id": str(session.public_id)},
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def revoke_others(self, request):
        current_session = request.auth
        queryset = self.get_queryset().exclude(id=current_session.id)
        count = 0
        for session in queryset.filter(is_active=True):
            SessionService.revoke_session(session=session)
            AuthEventService.log(
                event_type=AuthEventLog.EventType.SESSION_REVOKED,
                user=request.user,
                request=request,
                metadata={"session_id": str(session.public_id)},
            )
            count += 1
        return Response({"revoked_sessions": count}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        tags=["Auth"],
        summary="Listar convites de empresa",
        description="Lista convites de company/workspace disponíveis no ecossistema.",
        responses={200: CompanyInvitationSerializer, **common_error_responses()},
    ),
    retrieve=extend_schema(
        tags=["Auth"],
        summary="Detalhar convite",
        description="Retorna detalhes de um convite de empresa.",
        responses={200: CompanyInvitationSerializer, **common_error_responses(include_not_found=True)},
    ),
    create=extend_schema(
        tags=["Auth"],
        summary="Criar convite de empresa",
        description="Cria um convite para associar um usuario a uma empresa.",
        request=CompanyInvitationSerializer,
        responses={201: CompanyInvitationSerializer, **common_error_responses()},
    ),
    accept=extend_schema(
        tags=["Auth"],
        summary="Aceitar convite de empresa",
        description="Aceita um convite existente vinculando usuario atual ou criando novo usuario.",
        request=CompanyInvitationAcceptSerializer,
        responses={200: OpenApiResponse(description="Convite aceito."), **common_error_responses()},
    ),
)
class CompanyInvitationViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyInvitationSerializer

    def get_queryset(self):
        return CompanyInvitation.objects.select_related("company", "invited_role", "invited_by").all().order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(invited_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = InvitationService.create_invitation(
            company=serializer.validated_data["company"],
            invited_email=serializer.validated_data["invited_email"],
            invited_role=serializer.validated_data.get("invited_role"),
            invited_by=request.user,
            message=serializer.validated_data.get("message", ""),
        )
        output = CompanyInvitationSerializer(invitation, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def accept(self, request):
        serializer = CompanyInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation, user = InvitationService.accept_invitation(
                token=serializer.validated_data["token"],
                user=request.user if request.user and request.user.is_authenticated else None,
                first_name=serializer.validated_data.get("first_name", ""),
                last_name=serializer.validated_data.get("last_name", ""),
                password=serializer.validated_data.get("password", ""),
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "invitation": CompanyInvitationSerializer(invitation).data,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Auth"],
        summary="Listar eventos de autenticacao",
        description="Lista eventos relevantes de autenticacao e seguranca do usuario ou da plataforma.",
        responses={200: AuthEventLogSerializer, **common_error_responses()},
    )
)
class AuthEventLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AuthEventLogSerializer

    def get_queryset(self):
        queryset = AuthEventLog.objects.select_related("user").all()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)


class MyOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Consultar onboarding",
        description="Retorna o estado de onboarding do usuario autenticado.",
        responses={200: OnboardingProfileSerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        profile, _ = OnboardingProfile.objects.get_or_create(
            user=request.user,
            defaults={"email_verified": request.user.is_verified},
        )
        return Response(OnboardingProfileSerializer(profile).data)

    @extend_schema(
        tags=["Auth"],
        summary="Atualizar onboarding",
        description="Atualiza o progresso de onboarding do usuario autenticado.",
        request=OnboardingProfileSerializer,
        responses={200: OnboardingProfileSerializer, **common_error_responses()},
    )
    def patch(self, request, *args, **kwargs):
        profile, _ = OnboardingProfile.objects.get_or_create(
            user=request.user,
            defaults={"email_verified": request.user.is_verified},
        )
        serializer = OnboardingProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        if profile.profile_completed and profile.company_setup_completed and profile.email_verified:
            profile.onboarding_status = OnboardingProfile.Status.COMPLETED
            profile.completed_at = profile.completed_at or timezone.now()
            profile.save(update_fields=["onboarding_status", "completed_at", "updated_at"])
        return Response(OnboardingProfileSerializer(profile).data)
