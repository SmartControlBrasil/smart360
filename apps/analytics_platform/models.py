import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class AnalyticsEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_type = models.CharField(max_length=120, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=120, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="analytics_events",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="analytics_events",
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_events"
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.source_module}:{self.event_type}"


class AnalyticsMetric(models.Model):
    class MetricType(models.TextChoices):
        COUNTER = "counter", "Counter"
        GAUGE = "gauge", "Gauge"
        PERCENTAGE = "percentage", "Percentage"
        CURRENCY = "currency", "Currency"
        DURATION = "duration", "Duration"
        RATIO = "ratio", "Ratio"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    metric_name = models.CharField(max_length=160)
    metric_slug = models.SlugField(max_length=180, unique=True, blank=True)
    metric_type = models.CharField(max_length=20, choices=MetricType.choices, default=MetricType.COUNTER)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_metrics"
        ordering = ["metric_name"]

    def save(self, *args, **kwargs):
        if not self.metric_slug:
            self.metric_slug = slugify(self.metric_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.metric_name


class AnalyticsDimension(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_dimensions"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AnalyticsMetricValue(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    metric = models.ForeignKey(
        "analytics_platform.AnalyticsMetric",
        on_delete=models.CASCADE,
        related_name="values",
    )
    dimension = models.ForeignKey(
        "analytics_platform.AnalyticsDimension",
        on_delete=models.SET_NULL,
        related_name="metric_values",
        null=True,
        blank=True,
    )
    dimension_value = models.CharField(max_length=160, blank=True)
    value = models.DecimalField(max_digits=18, decimal_places=4)
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)
    reference_date = models.DateField(null=True, blank=True, db_index=True)
    source_module = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_metric_values"
        ordering = ["-calculated_at", "-created_at"]
        indexes = [
            models.Index(fields=["source_module", "reference_date"], name="analytics_mv_src_ref_idx"),
        ]

    def __str__(self) -> str:
        if self.dimension and self.dimension_value:
            return f"{self.metric} [{self.dimension}:{self.dimension_value}]"
        return str(self.metric)


class AnalyticsReport(models.Model):
    class ReportType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        EXECUTIVE = "executive", "Executive"
        FINANCIAL = "financial", "Financial"
        TECHNICAL = "technical", "Technical"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.OPERATIONAL)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_reports"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AnalyticsDashboard(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    layout_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_dashboards"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AnalyticsWidget(models.Model):
    class WidgetType(models.TextChoices):
        METRIC_CARD = "metric_card", "Metric Card"
        LINE_CHART = "line_chart", "Line Chart"
        BAR_CHART = "bar_chart", "Bar Chart"
        PIE_CHART = "pie_chart", "Pie Chart"
        TABLE = "table", "Table"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    dashboard = models.ForeignKey(
        "analytics_platform.AnalyticsDashboard",
        on_delete=models.CASCADE,
        related_name="widgets",
    )
    widget_type = models.CharField(max_length=30, choices=WidgetType.choices, default=WidgetType.METRIC_CARD)
    title = models.CharField(max_length=160)
    metric = models.ForeignKey(
        "analytics_platform.AnalyticsMetric",
        on_delete=models.SET_NULL,
        related_name="widgets",
        null=True,
        blank=True,
    )
    config_json = models.JSONField(default=dict, blank=True)
    ordering = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_widgets"
        ordering = ["dashboard__name", "ordering", "title"]
        constraints = [
            models.UniqueConstraint(fields=["dashboard", "ordering"], name="uniq_analytics_widget_dashboard_ordering"),
        ]

    def __str__(self) -> str:
        return f"{self.dashboard}: {self.title}"


class AnalyticsSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    snapshot_type = models.CharField(max_length=120, db_index=True)
    snapshot_date = models.DateField(db_index=True)
    data_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_snapshots"
        ordering = ["-snapshot_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.snapshot_type} @ {self.snapshot_date}"


class OperationalMetrics(models.Model):
    class PeriodType(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="operational_metrics",
    )
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    total_work_orders = models.PositiveIntegerField(default=0)
    total_preventives = models.PositiveIntegerField(default=0)
    total_correctives = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    avg_response_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_execution_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sla_compliance_rate = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_sla_compliant = models.PositiveIntegerField(default=0)
    total_sla_violated = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_operational_metrics"
        ordering = ["-period_start", "company__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "period_type", "period_start"],
                name="uniq_analytics_operational_metrics_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company} {self.period_type} {self.period_start}"


class ClientProfitability(models.Model):
    class PeriodType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="client_profitability_snapshots",
    )
    client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.CASCADE,
        related_name="profitability_snapshots",
    )
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_work_orders = models.PositiveIntegerField(default=0)
    total_assets = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_client_profitability"
        ordering = ["-period_start", "client__display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "period_type", "period_start"],
                name="uniq_analytics_client_profitability_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.client} {self.period_type} {self.period_start}"


class ContractProfitability(models.Model):
    class PeriodType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="contract_profitability_snapshots",
    )
    contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.CASCADE,
        related_name="profitability_snapshots",
    )
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_work_orders = models.PositiveIntegerField(default=0)
    total_assets = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_contract_profitability"
        ordering = ["-period_start", "contract__contract_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "period_type", "period_start"],
                name="uniq_analytics_contract_profitability_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.contract} {self.period_type} {self.period_start}"


class TechnicianPerformance(models.Model):
    class PeriodType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_performance_snapshots",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technician_performance_snapshots",
    )
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    jobs_completed = models.PositiveIntegerField(default=0)
    jobs_in_progress = models.PositiveIntegerField(default=0)
    avg_execution_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customer_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    profit_generated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_labor_minutes = models.PositiveIntegerField(default=0)
    total_response_minutes = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_technician_performance"
        ordering = ["-period_start", "technician__email"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "technician", "period_type", "period_start"],
                name="uniq_analytics_technician_performance_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.technician} {self.period_type} {self.period_start}"
