import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class AITaskType(models.Model):
    class TaskCategory(models.TextChoices):
        SUMMARIZATION = "summarization", "Summarization"
        CLASSIFICATION = "classification", "Classification"
        EXTRACTION = "extraction", "Extraction"
        RECOMMENDATION = "recommendation", "Recommendation"
        GENERATION = "generation", "Generation"
        DIAGNOSIS = "diagnosis", "Diagnosis"
        SEARCH_ENRICHMENT = "search_enrichment", "Search Enrichment"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    task_category = models.CharField(max_length=30, choices=TaskCategory.choices, default=TaskCategory.GENERATION)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_task_types"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class PromptTemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    task_type = models.ForeignKey(
        "ai_automation_center.AITaskType",
        on_delete=models.CASCADE,
        related_name="prompt_templates",
    )
    source_module = models.CharField(max_length=80, blank=True, db_index=True)
    prompt_role = models.CharField(max_length=80, blank=True)
    prompt_template = models.TextField()
    expected_output_schema = models.JSONField(default=dict, blank=True)
    model_hint = models.CharField(max_length=120, blank=True)
    version_label = models.CharField(max_length=40, default="v1")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_prompt_templates",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_prompt_templates"
        ordering = ["name", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.version_label}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class PromptVersion(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    prompt_template = models.ForeignKey(
        "ai_automation_center.PromptTemplate",
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_label = models.CharField(max_length=40)
    prompt_template_snapshot = models.TextField()
    expected_output_schema = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_prompt_versions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_prompt_versions"
        ordering = ["prompt_template__name", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["prompt_template", "version_label"],
                name="uniq_ai_prompt_template_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.prompt_template} {self.version_label}"


class AIContextProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    source_module = models.CharField(max_length=80, db_index=True)
    description = models.TextField(blank=True)
    context_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_context_profiles"
        ordering = ["source_module", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AIModelConfig(models.Model):
    class ModelType(models.TextChoices):
        CHAT = "chat", "Chat"
        COMPLETION = "completion", "Completion"
        EMBEDDING = "embedding", "Embedding"
        CLASSIFIER = "classifier", "Classifier"
        RERANKER = "reranker", "Reranker"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    provider_name = models.CharField(max_length=80)
    model_identifier = models.CharField(max_length=160)
    model_type = models.CharField(max_length=20, choices=ModelType.choices, default=ModelType.CHAT)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_model_configs"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AITaskRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task_type = models.ForeignKey(
        "ai_automation_center.AITaskType",
        on_delete=models.CASCADE,
        related_name="task_requests",
    )
    prompt_template = models.ForeignKey(
        "ai_automation_center.PromptTemplate",
        on_delete=models.SET_NULL,
        related_name="task_requests",
        null=True,
        blank=True,
    )
    context_profile = models.ForeignKey(
        "ai_automation_center.AIContextProfile",
        on_delete=models.SET_NULL,
        related_name="task_requests",
        null=True,
        blank=True,
    )
    source_module = models.CharField(max_length=80, db_index=True)
    source_reference_type = models.CharField(max_length=80, blank=True)
    source_reference_id = models.CharField(max_length=120, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_task_requests",
        null=True,
        blank=True,
    )
    input_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    model_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_task_requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_type} [{self.status}]"


class AITaskExecution(models.Model):
    class ExecutionMode(models.TextChoices):
        SYNC = "sync", "Sync"
        ASYNC = "async", "Async"
        MANUAL = "manual", "Manual"
        SIMULATED = "simulated", "Simulated"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task_request = models.ForeignKey(
        "ai_automation_center.AITaskRequest",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    execution_mode = models.CharField(max_length=20, choices=ExecutionMode.choices, default=ExecutionMode.SIMULATED)
    provider_name = models.CharField(max_length=80, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    prompt_snapshot = models.TextField(blank=True)
    input_snapshot = models.JSONField(default=dict, blank=True)
    output_text = models.TextField(blank=True)
    output_json = models.JSONField(default=dict, blank=True)
    token_usage_input = models.PositiveIntegerField(null=True, blank=True)
    token_usage_output = models.PositiveIntegerField(null=True, blank=True)
    cost_estimate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_task_executions"
        ordering = ["-started_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.task_request} execution"


class AIGeneratedArtifact(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task_execution = models.ForeignKey(
        "ai_automation_center.AITaskExecution",
        on_delete=models.CASCADE,
        related_name="generated_artifacts",
    )
    artifact_type = models.CharField(max_length=80, db_index=True)
    title = models.CharField(max_length=180, blank=True)
    content_text = models.TextField(blank=True)
    content_json = models.JSONField(default=dict, blank=True)
    related_file = models.ForeignKey(
        "files_center.StoredFile",
        on_delete=models.SET_NULL,
        related_name="ai_generated_artifacts",
        null=True,
        blank=True,
    )
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_ai_generated_artifacts",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_generated_artifacts"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.is_approved and self.approved_at is None:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.artifact_type


class AutomationRule(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    source_module = models.CharField(max_length=80, db_index=True)
    trigger_event = models.CharField(max_length=120, db_index=True)
    task_type = models.ForeignKey(
        "ai_automation_center.AITaskType",
        on_delete=models.CASCADE,
        related_name="automation_rules",
    )
    prompt_template = models.ForeignKey(
        "ai_automation_center.PromptTemplate",
        on_delete=models.SET_NULL,
        related_name="automation_rules",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    config_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_automation_rules"
        ordering = ["source_module", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AutomationExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    automation_rule = models.ForeignKey(
        "ai_automation_center.AutomationRule",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    source_reference_type = models.CharField(max_length=80, blank=True)
    source_reference_id = models.CharField(max_length=120, blank=True)
    integration_event_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    output_summary = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_automation_executions"
        ordering = ["-started_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.automation_rule} [{self.status}]"


class AIAnnotation(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    generated_artifact = models.ForeignKey(
        "ai_automation_center.AIGeneratedArtifact",
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    annotation_type = models.CharField(max_length=80)
    annotated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_annotations",
        null=True,
        blank=True,
    )
    feedback_label = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_annotations"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.annotation_type


class RetrievalSourceConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    source_type = models.CharField(max_length=80)
    source_module = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_retrieval_source_configs"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

