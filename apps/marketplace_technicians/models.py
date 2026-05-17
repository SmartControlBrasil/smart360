import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TechnicianProfile(models.Model):
    class ProfileType(models.TextChoices):
        INDEPENDENT = "independent", "Independent"
        COMPANY = "company", "Company"
        INTERNAL = "internal", "Internal"

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="technician_profile")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="technician_profiles",
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=180)
    document_number = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    bio = models.TextField(blank=True)
    certifications = models.JSONField(default=list, blank=True)
    profile_type = models.CharField(max_length=20, choices=ProfileType.choices, default=ProfileType.INDEPENDENT)
    experience_years = models.PositiveIntegerField(null=True, blank=True)
    service_radius_km = models.PositiveIntegerField(default=30)
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
    rating_average = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    completed_jobs_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_profiles"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class TechnicianSkill(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_skills"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class TechnicianSkillAssignment(models.Model):
    class ProficiencyLevel(models.TextChoices):
        BASIC = "basic", "Basic"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        SPECIALIST = "specialist", "Specialist"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="skill_assignments",
    )
    skill = models.ForeignKey(
        "marketplace_technicians.TechnicianSkill",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    proficiency_level = models.CharField(
        max_length=20,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
    )
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_skill_assignments"
        ordering = ["technician_profile__display_name", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["technician_profile", "skill"],
                name="uniq_marketplace_technician_skill",
            ),
        ]


class ServiceRegion(models.Model):
    class RegionType(models.TextChoices):
        CITY = "city", "City"
        STATE = "state", "State"
        METROPOLITAN = "metropolitan", "Metropolitan"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    region_type = models.CharField(max_length=20, choices=RegionType.choices, default=RegionType.CITY)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_service_regions"
        ordering = ["state", "city", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "state", "city", "region_type"],
                name="uniq_marketplace_service_region",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class TechnicianServiceRegion(models.Model):
    class CoverageType(models.TextChoices):
        LOCAL = "local", "Local"
        TRAVEL = "travel", "Travel"
        REMOTE = "remote", "Remote"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="service_regions",
    )
    service_region = models.ForeignKey(
        "marketplace_technicians.ServiceRegion",
        on_delete=models.CASCADE,
        related_name="technicians",
    )
    coverage_type = models.CharField(
        max_length=20,
        choices=CoverageType.choices,
        default=CoverageType.LOCAL,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_service_regions"
        ordering = ["technician_profile__display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["technician_profile", "service_region"],
                name="uniq_marketplace_technician_region",
            ),
        ]


class TechnicianAvailability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"
        SUNDAY = 7, "Sunday"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="availabilities",
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_availabilities"
        ordering = ["technician_profile__display_name", "weekday", "start_time"]


class TechnicianPortfolioItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="portfolio_items",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    media_file = models.FileField(upload_to="marketplace_technicians/portfolio/", null=True, blank=True)
    media_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_portfolio_items"
        ordering = ["ordering", "-created_at"]


class TechnicianServiceRequest(models.Model):
    class ServiceType(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance"
        INSTALLATION = "installation", "Installation"
        INSPECTION = "inspection", "Inspection"
        EMERGENCY = "emergency", "Emergency"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MATCHING = "matching", "Matching"
        OFFERS_RECEIVED = "offers_received", "Offers Received"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Origin(models.TextChoices):
        DIRECT = "direct", "Marketplace Direct"
        SMART_SYSTEM = "smart_system", "Smart System"
        MANUAL = "manual", "Manual"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    requester_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="technician_service_requests",
        null=True,
        blank=True,
    )
    requester_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="technician_service_requests",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.CharField(max_length=120, blank=True)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    requested_date = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address_line = models.CharField(max_length=255, blank=True)
    location_label = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.DIRECT)
    related_client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.SET_NULL,
        related_name="technician_requests",
        null=True,
        blank=True,
    )
    related_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="technician_requests",
        null=True,
        blank=True,
    )
    related_asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="technician_requests",
        null=True,
        blank=True,
    )
    related_service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="technician_requests",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_service_requests"
        ordering = ["-created_at"]


class TechnicianServiceOffer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    service_request = models.ForeignKey(
        "marketplace_technicians.TechnicianServiceRequest",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    proposed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    estimated_hours = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_service_offers"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request", "technician_profile"],
                name="uniq_marketplace_service_offer_per_technician",
            ),
        ]


class TechnicianMatchingRecord(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        NOTIFIED = "notified", "Notified"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_service_request = models.ForeignKey(
        "marketplace_technicians.TechnicianServiceRequest",
        on_delete=models.CASCADE,
        related_name="matching_records",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="matching_records",
    )
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_specialty = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_distance = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_experience = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_availability = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_response_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ranking_position = models.PositiveIntegerField(null=True, blank=True)
    scoring_version = models.CharField(max_length=32, default="v1")
    match_reason = models.TextField(blank=True)
    calculation_context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_matching_records"
        ordering = ["-match_score", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["technician_service_request", "technician_profile"],
                name="uniq_marketplace_matching_record",
            ),
        ]


class TechnicianAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_service_request = models.ForeignKey(
        "marketplace_technicians.TechnicianServiceRequest",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    service_offer = models.OneToOneField(
        "marketplace_technicians.TechnicianServiceOffer",
        on_delete=models.SET_NULL,
        related_name="assignment",
        null=True,
        blank=True,
    )
    assignment_status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_assignments"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["technician_service_request", "technician_profile"],
                name="uniq_marketplace_assignment",
            ),
        ]


class TechnicianWorkReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_assignment = models.OneToOneField(
        "marketplace_technicians.TechnicianAssignment",
        on_delete=models.CASCADE,
        related_name="work_report",
    )
    summary = models.CharField(max_length=255)
    execution_notes = models.TextField(blank=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    labor_minutes = models.PositiveIntegerField(default=0)
    materials_used = models.JSONField(default=list, blank=True)
    next_recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_work_reports"
        ordering = ["-created_at"]


class TechnicianReview(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        PENDING = "pending", "Pending"
        FLAGGED = "flagged", "Flagged"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    assignment = models.ForeignKey(
        "marketplace_technicians.TechnicianAssignment",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="technician_reviews",
        null=True,
        blank=True,
    )
    reviewer_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="technician_reviews",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_reviews"
        ordering = ["-created_at"]


class TechnicianCompensationRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    technician_assignment = models.OneToOneField(
        "marketplace_technicians.TechnicianAssignment",
        on_delete=models.CASCADE,
        related_name="compensation_record",
    )
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_technician_compensations"
        ordering = ["-created_at"]
