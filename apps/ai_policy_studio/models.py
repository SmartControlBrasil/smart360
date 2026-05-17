import uuid

from django.conf import settings
from django.db import models


class Policy(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    tenant_scope = models.CharField(max_length=20, default="global", db_index=True)
    is_global = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="policy_studio_policies_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_policy_studio_policies"
        ordering = ["name", "created_at"]


class PolicyScope(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey("ai_policy_studio.Policy", on_delete=models.CASCADE, related_name="scopes")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="policy_studio_scopes",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="policy_studio_scopes",
        null=True,
        blank=True,
    )
    module_slug = models.CharField(max_length=80, blank=True, db_index=True)
    action_type = models.CharField(max_length=80, blank=True, db_index=True)
    agent_slug = models.CharField(max_length=80, blank=True, db_index=True)
    copilot_key = models.CharField(max_length=80, blank=True, db_index=True)
    priority = models.PositiveIntegerField(default=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_policy_studio_scopes"
        ordering = ["priority", "id"]


class PolicyRule(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"
        ANY = "any", "Any"

    class EvaluationResult(models.TextChoices):
        ALLOW = "allow", "Allow"
        DENY = "deny", "Deny"
        REQUIRE_APPROVAL = "require_approval", "Require Approval"
        ESCALATE = "escalate", "Escalate"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey("ai_policy_studio.Policy", on_delete=models.CASCADE, related_name="rules")
    action_type = models.CharField(max_length=80, blank=True, db_index=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.ANY, db_index=True)
    autonomy_level = models.PositiveIntegerField(default=0)
    requires_approval = models.BooleanField(default=False)
    allowed = models.BooleanField(default=True)
    result = models.CharField(max_length=30, choices=EvaluationResult.choices, default=EvaluationResult.ALLOW, db_index=True)
    approver_roles = models.JSONField(default=list, blank=True)
    conditions = models.JSONField(default=dict, blank=True)
    rationale = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_policy_studio_rules"
        ordering = ["id"]


class PolicyVersion(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey("ai_policy_studio.Policy", on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict, blank=True)
    change_summary = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="policy_studio_versions_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_policy_studio_versions"
        ordering = ["-version_number", "-created_at"]
        unique_together = ("policy", "version_number")


class PolicyEvaluation(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey(
        "ai_policy_studio.Policy",
        on_delete=models.SET_NULL,
        related_name="evaluations",
        null=True,
        blank=True,
    )
    rule = models.ForeignKey(
        "ai_policy_studio.PolicyRule",
        on_delete=models.SET_NULL,
        related_name="evaluations",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="policy_studio_evaluations",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="policy_studio_evaluations",
        null=True,
        blank=True,
    )
    module_slug = models.CharField(max_length=80, blank=True, db_index=True)
    action_type = models.CharField(max_length=80, blank=True, db_index=True)
    result = models.CharField(max_length=30, db_index=True)
    reason = models.TextField(blank=True)
    context_payload = models.JSONField(default=dict, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_policy_studio_evaluations"
        ordering = ["-evaluated_at"]


class PolicySimulationRun(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey("ai_policy_studio.Policy", on_delete=models.CASCADE, related_name="simulation_runs")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="policy_studio_simulations",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="policy_studio_simulations",
        null=True,
        blank=True,
    )
    input_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="policy_studio_simulations_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_policy_studio_simulation_runs"
        ordering = ["-created_at"]

