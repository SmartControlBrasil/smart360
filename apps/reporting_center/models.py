import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ReportTemplate(models.Model):
    class ReportType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        MANAGERIAL = "managerial", "Managerial"
        FINANCIAL = "financial", "Financial"
        ANALYTICAL = "analytical", "Analytical"
        CUSTOM = "custom", "Custom"

    class OutputFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        JSON = "json", "JSON"
        PDF_FUTURE = "pdf_future", "PDF Future"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    source_module = models.CharField(max_length=80, db_index=True)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.OPERATIONAL)
    description = models.TextField(blank=True)
    output_format_default = models.CharField(max_length=20, choices=OutputFormat.choices, default=OutputFormat.JSON)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_templates"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ReportRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class OutputFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        JSON = "json", "JSON"
        PDF_FUTURE = "pdf_future", "PDF Future"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    template = models.ForeignKey("reporting_center.ReportTemplate", on_delete=models.PROTECT, related_name="requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_requests",
        null=True,
        blank=True,
    )
    requested_for_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="report_requests",
        null=True,
        blank=True,
    )
    source_module = models.CharField(max_length=80, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    output_format = models.CharField(max_length=20, choices=OutputFormat.choices, default=OutputFormat.JSON)
    filters_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_report_requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.template.name} [{self.status}]"


class ReportArtifact(models.Model):
    class ArtifactType(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        JSON = "json", "JSON"
        PDF_FUTURE = "pdf_future", "PDF Future"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    report_request = models.ForeignKey("reporting_center.ReportRequest", on_delete=models.CASCADE, related_name="artifacts")
    file = models.FileField(upload_to="reporting_center/artifacts/", blank=True)
    artifact_type = models.CharField(max_length=20, choices=ArtifactType.choices, default=ArtifactType.JSON)
    storage_path = models.CharField(max_length=255, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    generated_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_report_artifacts"
        ordering = ["-generated_at", "-created_at"]

    def __str__(self) -> str:
        return self.file_name or f"artifact-{self.public_id}"


class ExportProfile(models.Model):
    class ExportType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        LIST = "list", "List"
        ANALYTICAL = "analytical", "Analytical"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    source_module = models.CharField(max_length=80, db_index=True)
    export_type = models.CharField(max_length=20, choices=ExportType.choices, default=ExportType.OPERATIONAL)
    description = models.TextField(blank=True)
    columns_config = models.JSONField(default=list, blank=True)
    filters_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="export_profiles",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_export_profiles"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ExportExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class OutputFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        JSON = "json", "JSON"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    export_profile = models.ForeignKey("reporting_center.ExportProfile", on_delete=models.PROTECT, related_name="executions")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="export_executions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    output_format = models.CharField(max_length=20, choices=OutputFormat.choices, default=OutputFormat.JSON)
    filters_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_export_executions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.export_profile.name} [{self.status}]"


class ReportLog(models.Model):
    class LogLevel(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_module = models.CharField(max_length=80, db_index=True)
    report_request = models.ForeignKey(
        "reporting_center.ReportRequest",
        on_delete=models.SET_NULL,
        related_name="logs",
        null=True,
        blank=True,
    )
    export_execution = models.ForeignKey(
        "reporting_center.ExportExecution",
        on_delete=models.SET_NULL,
        related_name="logs",
        null=True,
        blank=True,
    )
    log_level = models.CharField(max_length=20, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.log_level}: {self.message[:60]}"


class ScheduledReport(models.Model):
    class ScheduleType(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        CUSTOM = "custom", "Custom"

    class OutputFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        JSON = "json", "JSON"
        PDF_FUTURE = "pdf_future", "PDF Future"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    template = models.ForeignKey("reporting_center.ReportTemplate", on_delete=models.PROTECT, related_name="scheduled_reports")
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="scheduled_reports",
        null=True,
        blank=True,
    )
    owner_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="scheduled_reports",
        null=True,
        blank=True,
    )
    schedule_type = models.CharField(max_length=20, choices=ScheduleType.choices, default=ScheduleType.WEEKLY)
    schedule_config = models.JSONField(default=dict, blank=True)
    output_format = models.CharField(max_length=20, choices=OutputFormat.choices, default=OutputFormat.JSON)
    filters_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_center_scheduled_reports"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

