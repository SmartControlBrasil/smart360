import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AutonomousModeConfig(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="autonomous_mode_configs",
        null=True,
        blank=True,
    )
    is_enabled = models.BooleanField(default=False)
    mode_level = models.PositiveSmallIntegerField(default=1)
    max_risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    allowed_action_types = models.JSONField(default=list, blank=True)
    blocked_action_types = models.JSONField(default=list, blank=True)
    requires_simulation_for = models.JSONField(default=list, blank=True)
    confidence_threshold_default = models.DecimalField(max_digits=5, decimal_places=2, default=0.80)
    confidence_threshold_overrides = models.JSONField(default=dict, blank=True)
    max_executions_per_hour = models.PositiveIntegerField(default=30)
    max_executions_per_day = models.PositiveIntegerField(default=200)
    max_failures_per_day = models.PositiveIntegerField(default=5)
    max_rollbacks_per_day = models.PositiveIntegerField(default=5)
    kill_switch_enabled = models.BooleanField(default=False)
    kill_switch_action_types = models.JSONField(default=list, blank=True)
    kill_switch_agents = models.JSONField(default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_autonomous_mode_configs"
        ordering = ["company_id", "-updated_at"]


class AutonomousExecution(models.Model):
    class ExecutionStatus(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        BLOCKED = "blocked", "Blocked"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    class RollbackStatus(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not Required"
        AVAILABLE = "available", "Available"
        EXECUTED = "executed", "Executed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="autonomous_executions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="autonomous_executions",
        null=True,
        blank=True,
    )
    action_type = models.CharField(max_length=80, db_index=True)
    source_agent = models.CharField(max_length=120, blank=True, db_index=True)
    source_decision = models.ForeignKey(
        "ai_decision_engine.AgentDecision",
        on_delete=models.SET_NULL,
        related_name="autonomous_executions",
        null=True,
        blank=True,
    )
    source_simulation = models.ForeignKey(
        "ai_simulation_engine.SimulationRun",
        on_delete=models.SET_NULL,
        related_name="autonomous_executions",
        null=True,
        blank=True,
    )
    risk_level = models.CharField(max_length=20, db_index=True)
    confidence_level = models.CharField(max_length=20, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    execution_status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.CANDIDATE, db_index=True)
    execution_summary = models.TextField(blank=True)
    rollback_supported = models.BooleanField(default=False)
    rollback_status = models.CharField(max_length=20, choices=RollbackStatus.choices, default=RollbackStatus.NOT_REQUIRED)
    policy_snapshot = models.JSONField(default=dict, blank=True)
    guard_snapshot = models.JSONField(default=dict, blank=True)
    expected_outcome = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_autonomous_executions"
        ordering = ["-created_at"]


class AutonomousExecutionGuard(models.Model):
    class GuardType(models.TextChoices):
        VOLUME = "volume", "Volume"
        FAILURE_RATE = "failure_rate", "Failure Rate"
        ROLLBACK_RATE = "rollback_rate", "Rollback Rate"
        CONFIDENCE = "confidence", "Confidence"
        INCIDENT = "incident", "Incident"
        KILL_SWITCH = "kill_switch", "Kill Switch"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="autonomous_guards",
        null=True,
        blank=True,
    )
    guard_type = models.CharField(max_length=30, choices=GuardType.choices, db_index=True)
    threshold_key = models.CharField(max_length=80, db_index=True)
    threshold_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_autonomous_execution_guards"
        ordering = ["company_id", "guard_type", "threshold_key"]


class AutonomousIncident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="autonomous_incidents",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="autonomous_incidents",
        null=True,
        blank=True,
    )
    autonomous_execution = models.ForeignKey(
        "ai_autonomous_ops.AutonomousExecution",
        on_delete=models.CASCADE,
        related_name="incidents",
        null=True,
        blank=True,
    )
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    incident_type = models.CharField(max_length=80, db_index=True)
    summary = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_autonomous_incidents"
        ordering = ["-created_at"]


class AutonomousAuditTrail(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    autonomous_execution = models.ForeignKey(
        "ai_autonomous_ops.AutonomousExecution",
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="autonomous_audit_entries",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=80, db_index=True)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_autonomous_audit_trail"
        ordering = ["created_at", "id"]

