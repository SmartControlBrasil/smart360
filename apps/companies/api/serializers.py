from rest_framework import serializers

from apps.companies.models import Company
from apps.companies.services.company_service import CompanyService


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "public_id",
            "name",
            "legal_name",
            "slug",
            "tax_id",
            "email",
            "phone_number",
            "website",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class CompanyCreateSerializer(serializers.ModelSerializer):
    role_codes = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        allow_empty=False,
        default=["company_owner"],
        write_only=True,
    )

    class Meta:
        model = Company
        fields = (
            "name",
            "legal_name",
            "slug",
            "tax_id",
            "email",
            "phone_number",
            "website",
            "status",
            "metadata",
            "role_codes",
        )

    def create(self, validated_data):
        request = self.context["request"]
        return CompanyService.create_company_with_owner(user=request.user, validated_data=validated_data)
