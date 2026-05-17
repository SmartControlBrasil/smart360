from rest_framework import serializers


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    environment = serializers.CharField()
    version = serializers.CharField(required=False)


class HealthCheckDetailsSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    environment = serializers.CharField()
    version = serializers.CharField()
    checks = serializers.DictField(child=serializers.JSONField())


class ApiRootSerializer(serializers.Serializer):
    name = serializers.CharField()
    version = serializers.CharField()
    modules = serializers.ListField(child=serializers.CharField())
    authentication = serializers.ListField(child=serializers.CharField())
