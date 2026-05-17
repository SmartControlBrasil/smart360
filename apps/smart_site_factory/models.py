import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Niche(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_niches"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Template(models.Model):
    class TemplateType(models.TextChoices):
        ONE_PAGE = "one_page", "One Page"
        MULTI_PAGE = "multi_page", "Multi Page"
        LANDING_PAGE = "landing_page", "Landing Page"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        DEPRECATED = "deprecated", "Deprecated"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    niche = models.ForeignKey("smart_site_factory.Niche", on_delete=models.PROTECT, related_name="templates")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=40, default="1.0.0")
    template_type = models.CharField(max_length=20, choices=TemplateType.choices, default=TemplateType.ONE_PAGE)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_templates"
        ordering = ["niche__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["niche", "name", "version"], name="uniq_ssf_template_version"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.version})"


class ConfiguratorQuestion(models.Model):
    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single Choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
        TEXT = "text", "Text"
        BOOLEAN = "boolean", "Boolean"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    niche = models.ForeignKey(
        "smart_site_factory.Niche",
        on_delete=models.CASCADE,
        related_name="questions",
        null=True,
        blank=True,
    )
    text = models.CharField(max_length=255)
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_configurator_questions"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.text


class ConfiguratorOption(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    question = models.ForeignKey(
        "smart_site_factory.ConfiguratorQuestion",
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_configurator_options"
        ordering = ["question__order", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "value"], name="uniq_ssf_option_per_question"),
        ]

    def __str__(self) -> str:
        return self.label


class TemplateRecommendationRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    niche = models.ForeignKey("smart_site_factory.Niche", on_delete=models.CASCADE, related_name="recommendation_rules")
    question = models.ForeignKey(
        "smart_site_factory.ConfiguratorQuestion",
        on_delete=models.CASCADE,
        related_name="recommendation_rules",
        null=True,
        blank=True,
    )
    option = models.ForeignKey(
        "smart_site_factory.ConfiguratorOption",
        on_delete=models.CASCADE,
        related_name="recommendation_rules",
        null=True,
        blank=True,
    )
    recommended_template = models.ForeignKey(
        "smart_site_factory.Template",
        on_delete=models.CASCADE,
        related_name="recommendation_rules",
    )
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_template_recommendation_rules"
        ordering = ["priority", "-created_at"]

    def __str__(self) -> str:
        return f"{self.niche} -> {self.recommended_template}"


class SiteOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        INTAKE_PENDING = "intake_pending", "Intake Pending"
        IN_PRODUCTION = "in_production", "In Production"
        REVIEW = "review", "Review"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="site_orders",
        null=True,
        blank=True,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="site_orders",
        null=True,
        blank=True,
    )
    niche = models.ForeignKey("smart_site_factory.Niche", on_delete=models.PROTECT, related_name="site_orders")
    selected_template = models.ForeignKey(
        "smart_site_factory.Template",
        on_delete=models.SET_NULL,
        related_name="selected_orders",
        null=True,
        blank=True,
    )
    recommended_template = models.ForeignKey(
        "smart_site_factory.Template",
        on_delete=models.SET_NULL,
        related_name="recommended_orders",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.INTAKE_PENDING)
    notes = models.TextField(blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    ordered_at = models.DateTimeField(default=timezone.now)
    production_started_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_site_orders"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.public_id} - {self.niche.name}"


class SiteOrderAnswer(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    site_order = models.ForeignKey("smart_site_factory.SiteOrder", on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(
        "smart_site_factory.ConfiguratorQuestion",
        on_delete=models.CASCADE,
        related_name="site_order_answers",
    )
    option = models.ForeignKey(
        "smart_site_factory.ConfiguratorOption",
        on_delete=models.SET_NULL,
        related_name="site_order_answers",
        null=True,
        blank=True,
    )
    value_text = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_site_order_answers"
        ordering = ["question__order", "id"]


class SiteProjectIntake(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    site_order = models.OneToOneField("smart_site_factory.SiteOrder", on_delete=models.CASCADE, related_name="intake")
    company_name = models.CharField(max_length=180)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    business_description = models.TextField(blank=True)
    main_services = models.JSONField(default=list, blank=True)
    instagram = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    photo_gallery = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_site_project_intakes"
        ordering = ["-created_at"]


class ProductionTask(models.Model):
    class Stage(models.TextChoices):
        DISCOVERY = "discovery", "Discovery"
        COPYWRITING = "copywriting", "Copywriting"
        DESIGN = "design", "Design"
        DEVELOPMENT = "development", "Development"
        QA = "qa", "QA"
        DELIVERY = "delivery", "Delivery"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    site_order = models.ForeignKey("smart_site_factory.SiteOrder", on_delete=models.CASCADE, related_name="production_tasks")
    stage = models.CharField(max_length=30, choices=Stage.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_site_tasks",
        null=True,
        blank=True,
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_production_tasks"
        ordering = ["site_order__created_at", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["site_order", "stage"], name="uniq_ssf_task_stage_per_order"),
        ]


class DeliveryRecord(models.Model):
    class AcceptanceStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    site_order = models.OneToOneField("smart_site_factory.SiteOrder", on_delete=models.CASCADE, related_name="delivery_record")
    delivered_url = models.URLField()
    delivered_at = models.DateTimeField(default=timezone.now)
    acceptance_status = models.CharField(
        max_length=30,
        choices=AcceptanceStatus.choices,
        default=AcceptanceStatus.PENDING,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ssf_delivery_records"
        ordering = ["-delivered_at"]
