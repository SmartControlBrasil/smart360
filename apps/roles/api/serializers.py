from rest_framework import serializers

from apps.roles.models import Role


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = (
            "public_id",
            "code",
            "label",
            "scope",
            "description",
            "is_system",
            "is_active",
            "metadata",
        )
        read_only_fields = fields
