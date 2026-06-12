from django.db import models


class LiviaConversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        QUALIFIED = "qualified", "Qualified"
        HANDED_OFF = "handed_off", "Handed off"
        CLOSED = "closed", "Closed"

    id = models.BigAutoField(primary_key=True)
    session_key = models.CharField(max_length=120, db_index=True)
    visitor_name = models.CharField(max_length=150, blank=True)
    visitor_email = models.EmailField(blank=True)
    visitor_phone = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    source_page = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "livia_conversations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_key", "status"]),
        ]

    def __str__(self) -> str:
        label = self.visitor_name or self.session_key
        return f"Lívia conversation #{self.pk} - {label}"


class LiviaMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        "livia_assistant.LiviaConversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "livia_messages"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:60]}"


class LiviaLeadCapture(models.Model):
    class OperationalStatus(models.TextChoices):
        NEW = "new", "New"
        SENT_TO_CRM = "sent_to_crm", "Sent to CRM"
        CONTACTED = "contacted", "Contacted"
        LOST = "lost", "Lost"
        CONVERTED = "converted", "Converted"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        EMERGENCY = "emergency", "Emergency"

    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        "livia_assistant.LiviaConversation",
        on_delete=models.CASCADE,
        related_name="lead_captures",
    )
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=120, blank=True)
    service_interest = models.CharField(max_length=180, blank=True)
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.MEDIUM)
    notes = models.TextField(blank=True)
    is_qualified = models.BooleanField(default=False)
    operational_status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NEW)
    crm_lead_id = models.PositiveBigIntegerField(null=True, blank=True)
    crm_reference = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "livia_lead_captures"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or self.company or f"Lead #{self.pk}"


class LiviaHandoffRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONTACTED = "contacted", "Contacted"
        RESOLVED = "resolved", "Resolved"
        CANCELED = "canceled", "Canceled"

    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        "livia_assistant.LiviaConversation",
        on_delete=models.CASCADE,
        related_name="handoff_requests",
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "livia_handoff_requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Handoff #{self.pk} - {self.status}"


class LiviaKnowledgeItem(models.Model):
    class Category(models.TextChoices):
        SERVICES = "services", "Services"
        COMPANY = "company", "Company"
        PRICING_POLICY = "pricing_policy", "Pricing policy"
        SAFETY = "safety", "Safety"
        FAQ = "faq", "FAQ"
        PROCESS = "process", "Process"
        TECHNICAL = "technical", "Technical"
        SMART360 = "smart360", "Smart360"

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.CharField(max_length=30, choices=Category.choices)
    content = models.TextField()
    keywords = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "livia_knowledge_items"
        ordering = ["-priority", "title"]

    def __str__(self) -> str:
        return self.title


class LiviaKnowledgeDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    source_type = models.CharField(max_length=40, default="markdown")
    category = models.CharField(max_length=100, blank=True, db_index=True)
    product = models.CharField(max_length=120, blank=True, db_index=True)
    application = models.CharField(max_length=120, blank=True, db_index=True)
    source_path = models.CharField(max_length=500, unique=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "livia_knowledge_documents"
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class LiviaKnowledgeChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(
        "livia_assistant.LiviaKnowledgeDocument",
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    token_estimate = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    # Compatibility storage for this first release. When pgvector is required in
    # every environment, migrate this field to pgvector.django.VectorField.
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "livia_knowledge_chunks"
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="livia_unique_document_chunk_index",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} #{self.chunk_index}"
