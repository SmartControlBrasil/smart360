import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class LeadSource(models.Model):
    class SourceType(models.TextChoices):
        ORGANIC = "organic", "Organic"
        PAID = "paid", "Paid"
        REFERRAL = "referral", "Referral"
        SOCIAL = "social", "Social"
        PARTNER = "partner", "Partner"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120, unique=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.ORGANIC)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_sources"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LeadTag(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_tags"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LeadCampaign(models.Model):
    class Channel(models.TextChoices):
        META = "meta", "Meta Ads"
        GOOGLE = "google", "Google Ads"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        ORGANIC = "organic", "Organic"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        FINISHED = "finished", "Finished"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=150)
    objective = models.CharField(max_length=180)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_campaigns"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        PROPOSAL = "proposal", "Proposal"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company_name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    niche = models.ForeignKey(
        "smart_site_factory.Niche",
        on_delete=models.SET_NULL,
        related_name="growth_leads",
        null=True,
        blank=True,
    )
    source = models.ForeignKey(
        "growth_engine.LeadSource",
        on_delete=models.SET_NULL,
        related_name="leads",
        null=True,
        blank=True,
    )
    campaign = models.ForeignKey(
        "growth_engine.LeadCampaign",
        on_delete=models.SET_NULL,
        related_name="leads",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    score = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField("growth_engine.LeadTag", related_name="leads", blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_leads",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_leads"
        ordering = ["-score", "-created_at"]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.contact_name or 'lead'})"


class LeadInteraction(models.Model):
    class InteractionType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        MEETING = "meeting", "Meeting"
        NOTE = "note", "Note"

    class Channel(models.TextChoices):
        PHONE = "phone", "Phone"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        INSTAGRAM = "instagram", "Instagram"
        OTHER = "other", "Other"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    lead = models.ForeignKey("growth_engine.Lead", on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    summary = models.TextField()
    happened_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="lead_interactions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_interactions"
        ordering = ["-happened_at"]


class LeadQualification(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    lead = models.OneToOneField("growth_engine.Lead", on_delete=models.CASCADE, related_name="qualification")
    criteria = models.JSONField(default=dict, blank=True)
    calculated_score = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_qualifications"


class LeadAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        REASSIGNED = "reassigned", "Reassigned"
        COMPLETED = "completed", "Completed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    lead = models.ForeignKey("growth_engine.Lead", on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lead_assignments",
    )
    status = models.CharField(max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.ACTIVE)
    assigned_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "growth_lead_assignments"
        ordering = ["-assigned_at"]
