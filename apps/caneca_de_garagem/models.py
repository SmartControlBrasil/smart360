import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CreativeStoreProfile(models.Model):
    class ProfileType(models.TextChoices):
        SUBLIMATION = "sublimation", "Sublimation"
        APPAREL = "apparel", "Apparel"
        HANDCRAFT = "handcraft", "Handcraft"
        MIXED = "mixed", "Mixed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vendor = models.OneToOneField("market_core.MarketplaceVendor", on_delete=models.CASCADE, related_name="creative_profile")
    display_name = models.CharField(max_length=180)
    bio = models.TextField(blank=True)
    profile_type = models.CharField(max_length=20, choices=ProfileType.choices, default=ProfileType.MIXED)
    production_capabilities = models.JSONField(default=list, blank=True)
    is_internal_factory = models.BooleanField(default=False)
    lead_time_days = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_creative_store_profiles"
        ordering = ["display_name"]


class CustomizationTemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey("market_core.MarketplaceProduct", on_delete=models.CASCADE, related_name="customization_templates")
    template_name = models.CharField(max_length=150)
    instructions = models.TextField(blank=True)
    allowed_text_fields = models.JSONField(default=list, blank=True)
    allowed_image_upload = models.BooleanField(default=True)
    max_images = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_customization_templates"
        ordering = ["template_name"]


class CustomizationRequest(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_item = models.OneToOneField("market_core.MarketplaceOrderItem", on_delete=models.CASCADE, related_name="customization_request")
    customization_template = models.ForeignKey(
        "caneca_de_garagem.CustomizationTemplate",
        on_delete=models.SET_NULL,
        related_name="requests",
        null=True,
        blank=True,
    )
    customer_text = models.JSONField(default=dict, blank=True)
    uploaded_assets = models.JSONField(default=list, blank=True)
    font_choice = models.CharField(max_length=120, blank=True)
    color_choice = models.CharField(max_length=120, blank=True)
    extra_notes = models.TextField(blank=True)
    approval_status = models.CharField(max_length=30, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_customization_requests"
        ordering = ["-created_at"]


class ArtworkAsset(models.Model):
    class AssetType(models.TextChoices):
        IMAGE = "image", "Image"
        VECTOR = "vector", "Vector"
        PDF = "pdf", "PDF"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VALIDATED = "validated", "Validated"
        REJECTED = "rejected", "Rejected"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customization_request = models.ForeignKey("caneca_de_garagem.CustomizationRequest", on_delete=models.CASCADE, related_name="artwork_assets")
    file = models.FileField(upload_to="caneca_de_garagem/assets/")
    asset_type = models.CharField(max_length=20, choices=AssetType.choices, default=AssetType.IMAGE)
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_artwork_assets"
        ordering = ["-created_at"]


class ProductionJob(models.Model):
    class JobType(models.TextChoices):
        ART_PREP = "art_prep", "Art Preparation"
        PRINT = "print", "Print"
        SUBLIMATION = "sublimation", "Sublimation"
        PACKAGING = "packaging", "Packaging"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order = models.ForeignKey("market_core.MarketplaceOrder", on_delete=models.CASCADE, related_name="production_jobs", null=True, blank=True)
    order_item = models.ForeignKey("market_core.MarketplaceOrderItem", on_delete=models.CASCADE, related_name="production_jobs", null=True, blank=True)
    vendor = models.ForeignKey("market_core.MarketplaceVendor", on_delete=models.SET_NULL, related_name="production_jobs", null=True, blank=True)
    internal_factory = models.ForeignKey(
        "caneca_de_garagem.CreativeStoreProfile",
        on_delete=models.SET_NULL,
        related_name="factory_jobs",
        null=True,
        blank=True,
    )
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    queue_position = models.PositiveIntegerField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="caneca_production_jobs",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_production_jobs"
        ordering = ["queue_position", "-created_at"]


class ProductionStep(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    production_job = models.ForeignKey("caneca_de_garagem.ProductionJob", on_delete=models.CASCADE, related_name="steps")
    step_name = models.CharField(max_length=150)
    ordering = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_production_steps"
        ordering = ["ordering", "id"]


class ShipmentPreparation(models.Model):
    class ShippingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        POSTED = "posted", "Posted"
        DELIVERED = "delivered", "Delivered"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order = models.OneToOneField("market_core.MarketplaceOrder", on_delete=models.CASCADE, related_name="shipment_preparation")
    shipping_status = models.CharField(max_length=20, choices=ShippingStatus.choices, default=ShippingStatus.PENDING)
    carrier = models.CharField(max_length=120, blank=True)
    tracking_code = models.CharField(max_length=120, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cdg_shipment_preparations"
        ordering = ["-created_at"]
