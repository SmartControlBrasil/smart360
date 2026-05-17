import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Experiment(models.Model):
    class TargetComponent(models.TextChoices):
        AGENT = "agent", "Agent"
        COPILOT = "copilot", "Copilot"
        DECISION_ENGINE = "decision_engine", "Decision Engine"
        SIMULATION_ENGINE = "simulation_engine", "Simulation Engine"
        POLICY = "policy", "Policy"
        HEURISTIC = "heuristic", "Heuristic"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        PROMOTED = "promoted", "Promoted"
        ARCHIVED = "archived", "Archived"

    class AssignmentStrategy(models.TextChoices):
        RANDOM = "random", "Random"
        WEIGHTED = "weighted", "Weighted"
        RULE_BASED = "rule_based", "Rule Based"

    class SuccessDirection(models.TextChoices):
        HIGHER_IS_BETTER = "higher_is_better", "Higher Is Better"
        LOWER_IS_BETTER = "lower_is_better", "Lower Is Better"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_experiments",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="ai_experiments",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    target_component = models.CharField(max_length=30, choices=TargetComponent.choices, db_index=True)
    target_reference = models.CharField(max_length=180, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    start_date = models.DateTimeField(default=timezone.now, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    traffic_split = models.JSONField(default=dict, blank=True)
    assignment_strategy = models.CharField(
        max_length=20,
        choices=AssignmentStrategy.choices,
        default=AssignmentStrategy.WEIGHTED,
        db_index=True,
    )
    primary_metric = models.CharField(max_length=80, default="effectiveness_score", db_index=True)
    success_direction = models.CharField(
        max_length=20,
        choices=SuccessDirection.choices,
        default=SuccessDirection.HIGHER_IS_BETTER,
    )
    min_sample_size = models.PositiveIntegerField(default=20)
    min_runtime_hours = models.PositiveIntegerField(default=24)
    auto_promote = models.BooleanField(default=False)
    configuration_payload = models.JSONField(default=dict, blank=True)
    winner_variant = models.ForeignKey(
        "ai_experimentation_framework.Variant",
        on_delete=models.SET_NULL,
        related_name="winning_experiments",
        null=True,
        blank=True,
    )
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_experiments_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_experimentation_experiments"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Variant(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    experiment = models.ForeignKey(
        "ai_experimentation_framework.Experiment",
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    config_payload = models.JSONField(default=dict, blank=True)
    weight = models.PositiveIntegerField(default=50)
    enabled = models.BooleanField(default=True)
    is_control = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_experimentation_variants"
        ordering = ["experiment_id", "name"]
        unique_together = ("experiment", "slug")

    def __str__(self):
        return f"{self.experiment.slug}:{self.slug}"


class ExperimentAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    experiment = models.ForeignKey(
        "ai_experimentation_framework.Experiment",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    variant = models.ForeignKey(
        "ai_experimentation_framework.Variant",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_experiment_assignments",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="ai_experiment_assignments",
        null=True,
        blank=True,
    )
    entity_key = models.CharField(max_length=180, db_index=True)
    entity_type = models.CharField(max_length=80, blank=True, db_index=True)
    assignment_reason = models.CharField(max_length=80, blank=True)
    context_payload = models.JSONField(default=dict, blank=True)
    assigned_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_experimentation_assignments"
        ordering = ["-assigned_at"]
        unique_together = ("experiment", "entity_key")


class ExperimentMetric(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    experiment = models.ForeignKey(
        "ai_experimentation_framework.Experiment",
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    variant = models.ForeignKey(
        "ai_experimentation_framework.Variant",
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    assignment = models.ForeignKey(
        "ai_experimentation_framework.ExperimentAssignment",
        on_delete=models.SET_NULL,
        related_name="metrics",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_experiment_metrics",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="ai_experiment_metrics",
        null=True,
        blank=True,
    )
    metric_type = models.CharField(max_length=80, db_index=True)
    value = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit = models.CharField(max_length=30, blank=True)
    source_component = models.CharField(max_length=80, blank=True, db_index=True)
    source_reference = models.CharField(max_length=180, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_experimentation_metrics"
        ordering = ["-recorded_at", "-id"]


class ExperimentResult(models.Model):
    class ConfidenceLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    experiment = models.OneToOneField(
        "ai_experimentation_framework.Experiment",
        on_delete=models.CASCADE,
        related_name="result",
    )
    winning_variant = models.ForeignKey(
        "ai_experimentation_framework.Variant",
        on_delete=models.SET_NULL,
        related_name="result_wins",
        null=True,
        blank=True,
    )
    summary = models.TextField(blank=True)
    primary_metric = models.CharField(max_length=80, blank=True)
    confidence_level = models.CharField(max_length=20, choices=ConfidenceLevel.choices, default=ConfidenceLevel.MEDIUM)
    result_payload = models.JSONField(default=dict, blank=True)
    recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_experimentation_results"
        ordering = ["-created_at"]


class ExperimentAuditTrail(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    experiment = models.ForeignKey(
        "ai_experimentation_framework.Experiment",
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    variant = models.ForeignKey(
        "ai_experimentation_framework.Variant",
        on_delete=models.SET_NULL,
        related_name="audit_entries",
        null=True,
        blank=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_experiment_audit_entries",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=80, db_index=True)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_experimentation_audit_trail"
        ordering = ["created_at", "id"]

