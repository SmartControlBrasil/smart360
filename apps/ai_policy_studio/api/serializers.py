from rest_framework import serializers

from apps.ai_policy_studio.models import Policy, PolicyEvaluation, PolicyRule, PolicyScope, PolicySimulationRun, PolicyVersion


class PolicyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyRule
        fields = "__all__"


class PolicyScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyScope
        fields = "__all__"


class PolicyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyVersion
        fields = "__all__"


class PolicyEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyEvaluation
        fields = "__all__"


class PolicySerializer(serializers.ModelSerializer):
    scopes = PolicyScopeSerializer(many=True, read_only=True)
    rules = PolicyRuleSerializer(many=True, read_only=True)
    versions = PolicyVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = "__all__"


class PolicySimulationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicySimulationRun
        fields = "__all__"


class PolicyEvaluateSerializer(serializers.Serializer):
    module_slug = serializers.CharField()
    action_type = serializers.CharField()
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    site = serializers.PrimaryKeyRelatedField(read_only=True)
    risk_level = serializers.CharField(required=False, allow_blank=True)
    autonomy_level = serializers.IntegerField(required=False, default=0)
    agent_slug = serializers.CharField(required=False, allow_blank=True)
    copilot_key = serializers.CharField(required=False, allow_blank=True)
    context = serializers.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.companies.models import Company
        from apps.smart_system.models import OperationalSite

        self.fields["company"].queryset = Company.objects.all()
        self.fields["site"].queryset = OperationalSite.objects.all()


class PolicyVersionCommandSerializer(serializers.Serializer):
    change_summary = serializers.CharField(required=False, allow_blank=True)
