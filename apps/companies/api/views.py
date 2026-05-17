from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from apps.companies.models import Company

from .serializers import CompanyCreateSerializer, CompanySerializer


class CompanyViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Company.objects.all().order_by("name")
    filterset_fields = ("status",)
    search_fields = ("name", "legal_name", "slug", "tax_id")
    ordering_fields = ("name", "created_at", "updated_at")

    def get_serializer_class(self):
        if self.action == "create":
            return CompanyCreateSerializer
        return CompanySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        output = CompanySerializer(company, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
