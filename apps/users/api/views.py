from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Membership
from apps.identity.services.identity_service import IdentityAuthService

from .serializers import BasicLoginSerializer, UserMembershipSerializer, UserSerializer


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = BasicLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, token = IdentityAuthService.login(request=request, **serializer.validated_data)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"token": token, "user": UserSerializer(user).data})


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class MyMembershipListView(generics.ListAPIView):
    serializer_class = UserMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Membership.objects.filter(user=self.request.user)
            .select_related("company")
            .prefetch_related("roles")
            .order_by("-is_primary", "company__name")
        )
