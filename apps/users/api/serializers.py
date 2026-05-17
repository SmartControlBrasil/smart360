from rest_framework import serializers

from apps.companies.models import Membership
from apps.roles.models import Role
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "public_id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "phone_number",
            "job_title",
            "department",
            "user_type",
            "is_active",
            "is_verified",
            "date_joined",
        )
        read_only_fields = fields


class BasicLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class MembershipRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("public_id", "code", "label", "scope")
        read_only_fields = fields


class UserMembershipSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source="company.public_id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    roles = MembershipRoleSerializer(many=True, read_only=True)

    class Meta:
        model = Membership
        fields = (
            "public_id",
            "company_id",
            "company_name",
            "status",
            "is_primary",
            "joined_at",
            "roles",
        )
        read_only_fields = fields
