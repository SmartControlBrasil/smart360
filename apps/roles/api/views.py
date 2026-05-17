from rest_framework import generics, permissions

from apps.roles.models import Role

from .serializers import RoleSerializer


class RoleListView(generics.ListAPIView):
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Role.objects.filter(is_active=True).order_by("scope", "label")
