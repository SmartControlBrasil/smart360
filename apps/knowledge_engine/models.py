import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class KnowledgeCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    parent = models.ForeignKey(
        "knowledge_engine.KnowledgeCategory",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_categories"
        ordering = ["ordering", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "parent"], name="uniq_knowledge_category_name_parent"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class EquipmentReference(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    equipment_type = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_equipment_references"
        ordering = ["manufacturer", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.model or self.manufacturer or ''}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class SymptomReference(models.Model):
    class SeverityLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    severity_level = models.CharField(max_length=20, choices=SeverityLevel.choices, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_symptom_references"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class FailureReference(models.Model):
    class Criticality(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    criticality = models.CharField(max_length=20, choices=Criticality.choices, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_failure_references"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CauseReference(models.Model):
    class CauseType(models.TextChoices):
        ELECTRICAL = "electrical", "Electrical"
        MECHANICAL = "mechanical", "Mechanical"
        HUMAN = "human", "Human"
        OPERATIONAL = "operational", "Operational"
        ENVIRONMENTAL = "environmental", "Environmental"
        OTHER = "other", "Other"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    cause_type = models.CharField(max_length=20, choices=CauseType.choices, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_cause_references"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class RecommendedAction(models.Model):
    class ActionType(models.TextChoices):
        INSPECTION = "inspection", "Inspection"
        REPAIR = "repair", "Repair"
        REPLACEMENT = "replacement", "Replacement"
        CLEANING = "cleaning", "Cleaning"
        CALIBRATION = "calibration", "Calibration"
        MONITORING = "monitoring", "Monitoring"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    action_type = models.CharField(max_length=20, choices=ActionType.choices, default=ActionType.INSPECTION)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_recommended_actions"
        ordering = ["title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class TroubleshootingArticle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    category = models.ForeignKey("knowledge_engine.KnowledgeCategory", on_delete=models.PROTECT, related_name="articles")
    summary = models.TextField(blank=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_articles_created",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_articles_reviewed",
        null=True,
        blank=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_troubleshooting_articles"
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class TechnicalDocument(models.Model):
    class DocumentType(models.TextChoices):
        MANUAL = "manual", "Manual"
        SERVICE_MANUAL = "service_manual", "Service Manual"
        DATASHEET = "datasheet", "Datasheet"
        PROCEDURE = "procedure", "Procedure"
        CHECKLIST = "checklist", "Checklist"
        TECHNICAL_BULLETIN = "technical_bulletin", "Technical Bulletin"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    category = models.ForeignKey("knowledge_engine.KnowledgeCategory", on_delete=models.PROTECT, related_name="technical_documents")
    equipment_reference = models.ForeignKey(
        "knowledge_engine.EquipmentReference",
        on_delete=models.SET_NULL,
        related_name="technical_documents",
        null=True,
        blank=True,
    )
    manufacturer = models.CharField(max_length=120, blank=True)
    version = models.CharField(max_length=40, blank=True)
    file = models.FileField(upload_to="knowledge_engine/documents/", null=True, blank=True)
    external_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="technical_documents_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_technical_documents"
        ordering = ["title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class KnowledgeTag(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_tags"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class KnowledgeLinkRule(models.Model):
    class ItemType(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        SYMPTOM = "symptom", "Symptom"
        FAILURE = "failure", "Failure"
        CAUSE = "cause", "Cause"
        ACTION = "action", "Action"
        ARTICLE = "article", "Article"
        DOCUMENT = "document", "Document"

    class RelationType(models.TextChoices):
        SYMPTOM_INDICATES_FAILURE = "symptom_indicates_failure", "Symptom Indicates Failure"
        FAILURE_HAS_CAUSE = "failure_has_cause", "Failure Has Cause"
        FAILURE_RECOMMENDED_ACTION = "failure_recommended_action", "Failure Recommended Action"
        EQUIPMENT_HAS_DOCUMENT = "equipment_has_document", "Equipment Has Document"
        ARTICLE_RELATES_EQUIPMENT = "article_relates_equipment", "Article Relates Equipment"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_type = models.CharField(max_length=30, choices=ItemType.choices)
    source_id = models.PositiveBigIntegerField()
    target_type = models.CharField(max_length=30, choices=ItemType.choices)
    target_id = models.PositiveBigIntegerField()
    relation_type = models.CharField(max_length=50, choices=RelationType.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_link_rules"
        ordering = ["relation_type", "-created_at"]


class EquipmentSymptomMap(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    equipment_reference = models.ForeignKey("knowledge_engine.EquipmentReference", on_delete=models.CASCADE, related_name="symptom_maps")
    symptom_reference = models.ForeignKey("knowledge_engine.SymptomReference", on_delete=models.CASCADE, related_name="equipment_maps")
    notes = models.TextField(blank=True)
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_equipment_symptom_maps"
        constraints = [
            models.UniqueConstraint(fields=["equipment_reference", "symptom_reference"], name="uniq_equipment_symptom_map"),
        ]


class SymptomFailureMap(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    symptom_reference = models.ForeignKey("knowledge_engine.SymptomReference", on_delete=models.CASCADE, related_name="failure_maps")
    failure_reference = models.ForeignKey("knowledge_engine.FailureReference", on_delete=models.CASCADE, related_name="symptom_maps")
    notes = models.TextField(blank=True)
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_symptom_failure_maps"
        constraints = [
            models.UniqueConstraint(fields=["symptom_reference", "failure_reference"], name="uniq_symptom_failure_map"),
        ]


class FailureCauseMap(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    failure_reference = models.ForeignKey("knowledge_engine.FailureReference", on_delete=models.CASCADE, related_name="cause_maps")
    cause_reference = models.ForeignKey("knowledge_engine.CauseReference", on_delete=models.CASCADE, related_name="failure_maps")
    notes = models.TextField(blank=True)
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_failure_cause_maps"
        constraints = [
            models.UniqueConstraint(fields=["failure_reference", "cause_reference"], name="uniq_failure_cause_map"),
        ]


class FailureActionMap(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    failure_reference = models.ForeignKey("knowledge_engine.FailureReference", on_delete=models.CASCADE, related_name="action_maps")
    recommended_action = models.ForeignKey("knowledge_engine.RecommendedAction", on_delete=models.CASCADE, related_name="failure_maps")
    notes = models.TextField(blank=True)
    priority = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_failure_action_maps"
        constraints = [
            models.UniqueConstraint(fields=["failure_reference", "recommended_action"], name="uniq_failure_action_map"),
        ]


class KnowledgeFeedback(models.Model):
    class ItemType(models.TextChoices):
        ARTICLE = "article", "Article"
        DOCUMENT = "document", "Document"
        EQUIPMENT = "equipment", "Equipment"
        FAILURE = "failure", "Failure"
        ACTION = "action", "Action"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_feedbacks",
        null=True,
        blank=True,
    )
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    item_id = models.PositiveBigIntegerField()
    usefulness_rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_feedbacks"
        ordering = ["-created_at"]
