import uuid

from django.db import models
from django.utils import timezone


class DigitalTwin(models.Model):
    class TwinType(models.TextChoices):
        SITE_OPERATIONAL = "site_operational_twin", "Site Operational Twin"
        ASSET_OPERATIONAL = "asset_operational_twin", "Asset Operational Twin"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ATTENTION = "attention", "Attention"
        CRITICAL = "critical", "Critical"
        INACTIVE = "inactive", "Inactive"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    twin_type = models.CharField(max_length=40, choices=TwinType.choices, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="digital_twins",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.CASCADE,
        related_name="digital_twins",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.CASCADE,
        related_name="digital_twins",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.SET_NULL,
        related_name="digital_twins",
        null=True,
        blank=True,
    )
    external_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW, db_index=True)
    current_state_summary = models.CharField(max_length=255, blank=True)
    state_payload = models.JSONField(default=dict, blank=True)
    risk_payload = models.JSONField(default=dict, blank=True)
    timeline_payload = models.JSONField(default=list, blank=True)
    summary_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_projected_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_digital_twins"
        ordering = ["-last_projected_at", "-updated_at"]
        indexes = [
            models.Index(fields=["company", "twin_type", "risk_level"], name="digital_twin_scope_idx"),
            models.Index(fields=["site", "asset"], name="digital_twin_entity_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.twin_type}:{self.public_id}"


class DigitalTwinSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    digital_twin = models.ForeignKey(
        "ai_digital_twin.DigitalTwin",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    snapshot_time = models.DateTimeField(default=timezone.now, db_index=True)
    state_payload = models.JSONField(default=dict, blank=True)
    risk_payload = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_digital_twin_snapshots"
        ordering = ["-snapshot_time", "-created_at"]


class DigitalTwinSignal(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    digital_twin = models.ForeignKey(
        "ai_digital_twin.DigitalTwin",
        on_delete=models.CASCADE,
        related_name="signals",
    )
    signal_type = models.CharField(max_length=80, db_index=True)
    source_type = models.CharField(max_length=80, db_index=True)
    source_reference = models.CharField(max_length=120, blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.LOW, db_index=True)
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    signal_payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_digital_twin_signals"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["digital_twin", "is_active", "severity"], name="digital_twin_signal_idx"),
        ]


class DigitalTwinProjection(models.Model):
    class ProjectionType(models.TextChoices):
        STATE = "state", "State"
        RISK = "risk", "Risk"
        TIMELINE = "timeline", "Timeline"
        INSIGHT = "insight", "Insight"

    class ProjectionStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        STALE = "stale", "Stale"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    digital_twin = models.ForeignKey(
        "ai_digital_twin.DigitalTwin",
        on_delete=models.CASCADE,
        related_name="projections",
    )
    projection_type = models.CharField(max_length=20, choices=ProjectionType.choices, db_index=True)
    projection_status = models.CharField(max_length=20, choices=ProjectionStatus.choices, default=ProjectionStatus.ACTIVE, db_index=True)
    source_window_start = models.DateTimeField(null=True, blank=True)
    source_window_end = models.DateTimeField(null=True, blank=True)
    projection_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_digital_twin_projections"
        ordering = ["projection_type", "-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["digital_twin", "projection_type"], name="uniq_digital_twin_projection_type"),
        ]

