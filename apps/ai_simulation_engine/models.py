import uuid

from django.conf import settings
from django.db import models


class SimulationType(models.Model):
    class PolicyMode(models.TextChoices):
        OPTIONAL = "optional", "Optional"
        RECOMMENDED = "recommended", "Recommended"
        REQUIRED = "required", "Required"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    policy_mode = models.CharField(max_length=20, choices=PolicyMode.choices, default=PolicyMode.OPTIONAL)
    heuristics_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_simulation_types"
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.name


class SimulationScenario(models.Model):
    class ScenarioStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    simulation_type = models.ForeignKey(
        "ai_simulation_engine.SimulationType",
        on_delete=models.PROTECT,
        related_name="scenarios",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="simulation_scenarios",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="simulation_scenarios",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    target_entity = models.CharField(max_length=80, blank=True, db_index=True)
    target_entity_id = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=ScenarioStatus.choices, default=ScenarioStatus.DRAFT, db_index=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="simulation_scenarios_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_simulation_scenarios"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class SimulationRun(models.Model):
    class TriggerType(models.TextChoices):
        MANUAL = "manual", "Manual"
        DECISION = "decision", "Decision"
        AGENT = "agent", "Agent"
        COPILOT = "copilot", "Copilot"
        API = "api", "API"

    class SourceType(models.TextChoices):
        DECISION = "decision", "Decision"
        PROPOSAL = "proposal", "Proposal"
        COPILOT = "copilot", "Copilot"
        AGENT = "agent", "Agent"
        DIRECT = "direct", "Direct"

    class RunStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    scenario = models.ForeignKey(
        "ai_simulation_engine.SimulationScenario",
        on_delete=models.CASCADE,
        related_name="runs",
    )
    decision = models.ForeignKey(
        "ai_decision_engine.AgentDecision",
        on_delete=models.SET_NULL,
        related_name="simulation_runs",
        null=True,
        blank=True,
    )
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.MANUAL)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.DIRECT)
    source_reference = models.CharField(max_length=180, blank=True, db_index=True)
    input_payload = models.JSONField(default=dict, blank=True)
    baseline_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.PENDING, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="simulation_runs_requested",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_simulation_runs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.scenario.title} [{self.status}]"


class SimulationResult(models.Model):
    class ConfidenceLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    simulation_run = models.OneToOneField(
        "ai_simulation_engine.SimulationRun",
        on_delete=models.CASCADE,
        related_name="result",
    )
    summary = models.TextField()
    impact_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    confidence_level = models.CharField(max_length=20, choices=ConfidenceLevel.choices, default=ConfidenceLevel.MEDIUM)
    risk_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sla_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    travel_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    workload_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recommendation = models.TextField(blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_simulation_results"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.simulation_run_id} result"


class SimulationAuditTrail(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    simulation_run = models.ForeignKey(
        "ai_simulation_engine.SimulationRun",
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    event_type = models.CharField(max_length=80, db_index=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="simulation_audit_entries",
        null=True,
        blank=True,
    )
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_simulation_audit_trail"
        ordering = ["created_at", "id"]


