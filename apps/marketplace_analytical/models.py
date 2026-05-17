import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class AnalyticalProvider(models.Model):
    class ProviderType(models.TextChoices):
        LABORATORY = "laboratory", "Laboratory"
        CONSULTANT = "consultant", "Consultant"
        ENGINEERING_FIRM = "engineering_firm", "Engineering Firm"
        SPECIALIST = "specialist", "Specialist"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        SUSPENDED = "suspended", "Suspended"
        BLOCKED = "blocked", "Blocked"

    class MarketplaceStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        AVAILABLE = "available", "Available"
        BUSY = "busy", "Busy"
        OFFLINE = "offline", "Offline"
        SUSPENDED = "suspended", "Suspended"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="analytical_providers",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="analytical_providers",
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=200, blank=True)
    document_number = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices, default=ProviderType.SPECIALIST)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    marketplace_status = models.CharField(
        max_length=20,
        choices=MarketplaceStatus.choices,
        default=MarketplaceStatus.PENDING,
    )
    trust_case_reference = models.CharField(max_length=100, blank=True)
    knowledge_profile_reference = models.CharField(max_length=100, blank=True)
    rating_average = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    completed_jobs_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_providers"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class AnalyticalServiceCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_service_categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AnalyticalService(models.Model):
    class ServiceType(models.TextChoices):
        ANALYSIS = "analysis", "Analysis"
        DIAGNOSTIC = "diagnostic", "Diagnostic"
        INSPECTION = "inspection", "Inspection"
        CONSULTING = "consulting", "Consulting"
        AUDIT = "audit", "Audit"

    class DeliveryType(models.TextChoices):
        REMOTE = "remote", "Remote"
        ON_SITE = "on_site", "On Site"
        HYBRID = "hybrid", "Hybrid"

    class PriceModel(models.TextChoices):
        FIXED = "fixed", "Fixed"
        QUOTE = "quote", "Quote"
        HOURLY = "hourly", "Hourly"
        PACKAGE = "package", "Package"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    provider = models.ForeignKey("marketplace_analytical.AnalyticalProvider", on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey("marketplace_analytical.AnalyticalServiceCategory", on_delete=models.PROTECT, related_name="services")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices, default=DeliveryType.REMOTE)
    estimated_turnaround_days = models.PositiveIntegerField(default=5)
    price_model = models.CharField(max_length=20, choices=PriceModel.choices, default=PriceModel.QUOTE)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="BRL")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_services"
        ordering = ["provider__display_name", "title"]


class AnalyticalServiceCapability(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_service = models.ForeignKey("marketplace_analytical.AnalyticalService", on_delete=models.CASCADE, related_name="capabilities")
    capability_name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_service_capabilities"
        ordering = ["analytical_service__title", "capability_name"]


class AnalyticalServiceRegion(models.Model):
    class CoverageType(models.TextChoices):
        LOCAL = "local", "Local"
        REGIONAL = "regional", "Regional"
        NATIONAL = "national", "National"
        INTERNATIONAL = "international", "International"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_service = models.ForeignKey("marketplace_analytical.AnalyticalService", on_delete=models.CASCADE, related_name="service_regions")
    region_name = models.CharField(max_length=120)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Brazil")
    coverage_type = models.CharField(max_length=20, choices=CoverageType.choices, default=CoverageType.LOCAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_service_regions"
        ordering = ["country", "state", "region_name"]


class AnalyticalRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MATCHING = "matching", "Matching"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Origin(models.TextChoices):
        DIRECT = "direct", "Marketplace Direct"
        SMART_SYSTEM = "smart_system", "Smart System"
        EXTERNAL = "external", "External Client"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    requester_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="analytical_requests",
        null=True,
        blank=True,
    )
    requester_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="analytical_requests",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.ForeignKey("marketplace_analytical.AnalyticalServiceCategory", on_delete=models.PROTECT, related_name="requests")
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    related_asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="analytical_requests",
        null=True,
        blank=True,
    )
    related_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="analytical_requests",
        null=True,
        blank=True,
    )
    related_service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="analytical_requests",
        null=True,
        blank=True,
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Brazil")
    requested_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.DIRECT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_requests"
        ordering = ["-requested_date"]


class AnalyticalMatchingRecord(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        NOTIFIED = "notified", "Notified"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_request = models.ForeignKey("marketplace_analytical.AnalyticalRequest", on_delete=models.CASCADE, related_name="matching_records")
    provider = models.ForeignKey("marketplace_analytical.AnalyticalProvider", on_delete=models.CASCADE, related_name="matching_records")
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    match_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_matching_records"
        ordering = ["-match_score", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["analytical_request", "provider"], name="uniq_marketplace_analytical_matching"),
        ]


class AnalyticalAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_request = models.ForeignKey("marketplace_analytical.AnalyticalRequest", on_delete=models.CASCADE, related_name="assignments")
    provider = models.ForeignKey("marketplace_analytical.AnalyticalProvider", on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_assignments"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(fields=["analytical_request", "provider"], name="uniq_marketplace_analytical_assignment"),
        ]


class AnalyticalReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_assignment = models.OneToOneField("marketplace_analytical.AnalyticalAssignment", on_delete=models.CASCADE, related_name="report")
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    report_file = models.FileField(upload_to="marketplace_analytical/reports/")
    technical_conclusion = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_reports"
        ordering = ["-created_at"]


class AnalyticalReview(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    analytical_assignment = models.ForeignKey("marketplace_analytical.AnalyticalAssignment", on_delete=models.CASCADE, related_name="reviews")
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="analytical_reviews",
        null=True,
        blank=True,
    )
    reviewer_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="analytical_reviews",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_analytical_reviews"
        ordering = ["-created_at"]
