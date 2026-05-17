import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class MaintenanceClient(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="maintenance_clients",
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=200, blank=True)
    document_number = models.CharField(max_length=40, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_clients"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class OperationalSite(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    maintenance_client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.CASCADE,
        related_name="operational_sites",
    )
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=40, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_operational_sites"
        ordering = ["maintenance_client__display_name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["maintenance_client", "name"], name="uniq_smart_system_site_name_per_client"),
        ]

    def __str__(self) -> str:
        return f"{self.maintenance_client} - {self.name}"


class AssetCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_asset_categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Asset(models.Model):
    class Status(models.TextChoices):
        OPERATING = "operating", "Operating"
        MAINTENANCE = "maintenance", "Maintenance"
        STOPPED = "stopped", "Stopped"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    class Criticality(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    operational_site = models.ForeignKey("smart_system.OperationalSite", on_delete=models.CASCADE, related_name="assets")
    category = models.ForeignKey("smart_system.AssetCategory", on_delete=models.PROTECT, related_name="assets")
    asset_tag = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=180)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    voltage = models.CharField(max_length=50, blank=True)
    power_rating = models.CharField(max_length=50, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    warranty_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPERATING)
    criticality = models.CharField(max_length=20, choices=Criticality.choices, default=Criticality.MEDIUM)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_assets"
        ordering = ["operational_site__name", "asset_tag"]

    def __str__(self) -> str:
        return f"{self.asset_tag} - {self.name}"


class EquipmentModel(models.Model):
    """
    Catalogo tecnico reutilizavel (nao representa instalacao em cliente).

    TODO(phase-2): mapear migracao gradual de Asset legado para CustomerEquipment + EquipmentModel.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DISCONTINUED = "discontinued", "Discontinued"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="smart_system_equipment_models",
    )
    name = models.CharField(max_length=180)
    category = models.ForeignKey(
        "smart_system.AssetCategory",
        on_delete=models.PROTECT,
        related_name="equipment_models",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    manufacturer_code = models.CharField(max_length=120, blank=True)
    equipment_type = models.CharField(max_length=120, blank=True)
    is_pmoc_applicable = models.BooleanField(default=False)
    pmoc_frequency = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_equipment_models"
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name", "manufacturer_code"],
                name="uniq_smart_system_equipment_model_company_name_code",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CustomerEquipment(models.Model):
    """
    Inventario operacional real por cliente/site.

    TODO(phase-2): integrar ServiceOrder para multi-equipamento via ServiceOrderEquipment.
    TODO(phase-3): integrar preventivas/checklists por CustomerEquipment.
    """

    class PreventiveGroup(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="customer_equipments",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.CASCADE,
        related_name="customer_equipments",
    )
    equipment_model = models.ForeignKey(
        "smart_system.EquipmentModel",
        on_delete=models.PROTECT,
        related_name="customer_equipments",
    )
    display_name = models.CharField(max_length=180, blank=True)
    customer_tag = models.CharField(max_length=60, db_index=True)
    internal_code = models.CharField(max_length=80, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=180, blank=True)
    preventive_group = models.CharField(max_length=1, choices=PreventiveGroup.choices, blank=True)
    is_pmoc_applicable = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    installed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_customer_equipments"
        ordering = ["company__name", "site__name", "customer_tag"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "customer_tag"],
                name="uniq_smart_system_customer_equipment_company_tag",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "site", "status"], name="sm_ce_scope_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.display_name and self.equipment_model_id:
            self.display_name = self.equipment_model.name
        if self.is_pmoc_applicable is None and self.equipment_model_id:
            self.is_pmoc_applicable = self.equipment_model.is_pmoc_applicable
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.display_name or self.equipment_model.name} - TAG: {self.customer_tag}"


class Checklist(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="smart_system_checklists",
        null=True,
        blank=True,
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.CASCADE,
        related_name="checklists",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_checklists"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ChecklistItem(models.Model):
    class ItemType(models.TextChoices):
        BOOLEAN = "boolean", "Boolean"
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        CHOICE = "choice", "Choice"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    checklist = models.ForeignKey("smart_system.Checklist", on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.BOOLEAN)
    ordering = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_checklist_items"
        ordering = ["checklist__name", "ordering", "id"]

    def __str__(self) -> str:
        return self.title


class MaintenancePlan(models.Model):
    class FrequencyType(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="smart_system_maintenance_plans",
        null=True,
        blank=True,
    )
    maintenance_contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.SET_NULL,
        related_name="maintenance_plans",
        null=True,
        blank=True,
    )
    contract_asset = models.ForeignKey(
        "smart_system.ContractAsset",
        on_delete=models.SET_NULL,
        related_name="maintenance_plans",
        null=True,
        blank=True,
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.CASCADE,
        related_name="maintenance_plans",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey("smart_system.Asset", on_delete=models.CASCADE, related_name="maintenance_plans", null=True, blank=True)
    category = models.ForeignKey(
        "smart_system.AssetCategory",
        on_delete=models.CASCADE,
        related_name="maintenance_plans",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    frequency_type = models.CharField(max_length=20, choices=FrequencyType.choices, default=FrequencyType.MONTHLY)
    frequency_value = models.PositiveIntegerField(default=1)
    estimated_duration_minutes = models.PositiveIntegerField(default=60)
    checklist = models.ForeignKey("smart_system.Checklist", on_delete=models.SET_NULL, related_name="maintenance_plans", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_maintenance_plans"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MaintenanceContract(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    class BillingFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        BIMONTHLY = "bimonthly", "Bimonthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMIANNUAL = "semiannual", "Semiannual"
        YEARLY = "yearly", "Yearly"
        CUSTOM_DAYS = "custom_days", "Custom Days"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="maintenance_contracts",
    )
    client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.CASCADE,
        related_name="maintenance_contracts",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="maintenance_contracts",
        null=True,
        blank=True,
    )
    contract_number = models.CharField(max_length=40, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    billing_frequency = models.CharField(
        max_length=20,
        choices=BillingFrequency.choices,
        default=BillingFrequency.MONTHLY,
    )
    billing_frequency_days = models.PositiveIntegerField(default=30)
    contract_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    next_billing_date = models.DateField(null=True, blank=True)
    last_billing_date = models.DateField(null=True, blank=True)
    auto_generate_preventives = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_maintenance_contracts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.contract_number


class ContractAsset(models.Model):
    class MaintenanceFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        BIMONTHLY = "bimonthly", "Bimonthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMIANNUAL = "semiannual", "Semiannual"
        YEARLY = "yearly", "Yearly"
        CUSTOM_DAYS = "custom_days", "Custom Days"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.CASCADE,
        related_name="covered_assets",
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.CASCADE,
        related_name="contract_links",
    )
    maintenance_frequency = models.CharField(
        max_length=20,
        choices=MaintenanceFrequency.choices,
        default=MaintenanceFrequency.MONTHLY,
    )
    maintenance_frequency_days = models.PositiveIntegerField(default=30)
    estimated_duration_minutes = models.PositiveIntegerField(default=120)
    last_execution = models.DateField(null=True, blank=True)
    next_execution = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_contract_assets"
        ordering = ["contract__contract_number", "asset__asset_tag"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "asset"],
                name="uniq_smart_system_contract_asset",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.contract.contract_number} - {self.asset.asset_tag}"


class ServiceOrder(models.Model):
    class MaintenanceType(models.TextChoices):
        PREVENTIVE = "preventive", "Preventive"
        CORRECTIVE = "corrective", "Corrective"
        INSPECTION = "inspection", "Inspection"
        INSTALLATION = "installation", "Installation"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING_QUOTE_APPROVAL = "waiting_quote_approval", "Waiting Quote Approval"
        WAITING_PARTS = "waiting_parts", "Waiting Parts"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        PLAN = "plan", "Maintenance Plan"
        ALERT = "alert", "Alert"
        FAILURE = "failure", "Failure"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_number = models.CharField(max_length=40, unique=True)
    client = models.ForeignKey("smart_system.MaintenanceClient", on_delete=models.PROTECT, related_name="service_orders")
    operational_site = models.ForeignKey("smart_system.OperationalSite", on_delete=models.PROTECT, related_name="service_orders")
    asset = models.ForeignKey("smart_system.Asset", on_delete=models.PROTECT, related_name="service_orders", null=True, blank=True)
    maintenance_contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.SET_NULL,
        related_name="service_orders",
        null=True,
        blank=True,
    )
    contract_asset = models.ForeignKey(
        "smart_system.ContractAsset",
        on_delete=models.SET_NULL,
        related_name="service_orders",
        null=True,
        blank=True,
    )
    maintenance_plan = models.ForeignKey(
        "smart_system.MaintenancePlan",
        on_delete=models.SET_NULL,
        related_name="service_orders",
        null=True,
        blank=True,
    )
    maintenance_type = models.CharField(max_length=20, choices=MaintenanceType.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.CharField(max_length=150, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_service_orders",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_service_orders",
        null=True,
        blank=True,
    )
    final_observations = models.TextField(blank=True)
    quote_status = models.CharField(max_length=20, blank=True)
    quote_required = models.BooleanField(default=False)
    quote_approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_service_orders"
        ordering = ["-opened_at"]

    def __str__(self) -> str:
        return self.order_number


class ServiceOrderChecklistResponse(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    service_order = models.ForeignKey("smart_system.ServiceOrder", on_delete=models.CASCADE, related_name="checklist_responses")
    checklist_item = models.ForeignKey("smart_system.ChecklistItem", on_delete=models.CASCADE, related_name="responses")
    response_boolean = models.BooleanField(null=True, blank=True)
    response_text = models.TextField(blank=True)
    response_number = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    response_choice = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_so_checklist_responses"
        ordering = ["checklist_item__ordering", "id"]


class FailureEvent(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ANALYZING = "analyzing", "Analyzing"
        RESOLVED = "resolved", "Resolved"
        MONITORED = "monitored", "Monitored"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("smart_system.Asset", on_delete=models.CASCADE, related_name="failure_events")
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="failure_events",
        null=True,
        blank=True,
    )
    detected_at = models.DateTimeField(default=timezone.now)
    symptom = models.TextField()
    probable_cause = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    downtime_minutes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_failure_events"
        ordering = ["-detected_at"]


class AssetHistoryEvent(models.Model):
    class EventType(models.TextChoices):
        SERVICE_ORDER_CREATED = "service_order_created", "Service Order Created"
        SERVICE_ORDER_COMPLETED = "service_order_completed", "Service Order Completed"
        FAILURE_REPORTED = "failure_reported", "Failure Reported"
        STATUS_CHANGED = "status_changed", "Status Changed"
        GENERAL = "general", "General"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("smart_system.Asset", on_delete=models.CASCADE, related_name="history_events")
    event_type = models.CharField(max_length=40, choices=EventType.choices, default=EventType.GENERAL)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    related_service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="asset_history_events",
        null=True,
        blank=True,
    )
    related_failure_event = models.ForeignKey(
        "smart_system.FailureEvent",
        on_delete=models.SET_NULL,
        related_name="asset_history_events",
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="asset_history_events",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_asset_history_events"
        ordering = ["-occurred_at"]


class WorkLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    service_order = models.ForeignKey("smart_system.ServiceOrder", on_delete=models.CASCADE, related_name="work_logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="work_logs",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    labor_minutes = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_work_logs"
        ordering = ["-started_at"]


class ServiceDocument(models.Model):
    class DocumentType(models.TextChoices):
        PHOTO = "photo", "Photo"
        REPORT = "report", "Report"
        INVOICE = "invoice", "Invoice"
        OTHER = "other", "Other"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    service_order = models.ForeignKey("smart_system.ServiceOrder", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="smart_system/documents/")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=180)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="service_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_service_documents"
        ordering = ["-created_at"]


class Part(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DISCONTINUED = "discontinued", "Discontinued"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="smart_system_parts",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="parts",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=30, default="un")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maximum_stock = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    primary_supplier = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_parts"
        ordering = ["company__name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="uniq_smart_system_part_company_code"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class PartAssetLink(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    part = models.ForeignKey("smart_system.Part", on_delete=models.CASCADE, related_name="asset_links")
    asset = models.ForeignKey("smart_system.Asset", on_delete=models.CASCADE, related_name="part_links")
    quantity_recommended = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_part_asset_links"
        ordering = ["asset__asset_tag", "part__code"]
        constraints = [
            models.UniqueConstraint(fields=["part", "asset"], name="uniq_smart_system_part_asset_link"),
        ]

    def __str__(self) -> str:
        return f"{self.part} -> {self.asset}"


class EquipmentModelPart(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="equipment_model_parts",
    )
    equipment_model = models.ForeignKey(
        "smart_system.EquipmentModel",
        on_delete=models.CASCADE,
        related_name="parts",
    )
    part = models.ForeignKey(
        "smart_system.Part",
        on_delete=models.CASCADE,
        related_name="equipment_models",
    )
    quantity_default = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_equipment_model_parts"
        ordering = ["equipment_model__name", "part__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "equipment_model", "part"],
                name="uniq_smart_system_equipment_model_part",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.equipment_model} -> {self.part}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"
        ADJUSTMENT = "adjustment", "Adjustment"
        RESERVED = "reserved", "Reserved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="smart_system_stock_movements",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    part = models.ForeignKey("smart_system.Part", on_delete=models.CASCADE, related_name="stock_movements")
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_stock_movements"
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.part.code} {self.movement_type} {self.quantity}"


class ServiceQuote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    quote_number = models.CharField(max_length=40, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="service_quotes",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="service_quotes",
        null=True,
        blank=True,
    )
    work_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="service_quotes",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    total_parts = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_labor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    customer_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    approved_by_name = models.CharField(max_length=180, blank=True)
    approved_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_service_quotes",
        null=True,
        blank=True,
    )
    approval_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_service_quotes",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_service_quotes",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_service_quotes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="smart_quote_company_status_idx"),
            models.Index(fields=["work_order", "status"], name="smart_quote_order_status_idx"),
        ]

    def __str__(self) -> str:
        return self.quote_number


class QuoteItem(models.Model):
    class ItemType(models.TextChoices):
        PART = "part", "Part"
        LABOR = "labor", "Labor"
        SERVICE = "service", "Service"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    quote = models.ForeignKey(
        "smart_system.ServiceQuote",
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    description = models.CharField(max_length=255)
    part_reference = models.CharField(max_length=120, blank=True)
    stock_item = models.ForeignKey(
        "smart_system.Part",
        on_delete=models.SET_NULL,
        related_name="quote_items",
        null=True,
        blank=True,
    )
    available_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_minutes = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_quote_items"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.description


class ServiceSignature(models.Model):
    class SignatureType(models.TextChoices):
        TECHNICIAN_COMPLETION = "technician_completion", "Technician Completion"
        CLIENT_ACCEPTANCE = "client_acceptance", "Client Acceptance"
        SUPERVISOR_VALIDATION = "supervisor_validation", "Supervisor Validation"
        REPORT_ACKNOWLEDGEMENT = "report_acknowledgement", "Report Acknowledgement"

    class SignerRole(models.TextChoices):
        TECHNICIAN = "technician", "Technician"
        CLIENT_RESPONSIBLE = "client_responsible", "Client Responsible"
        UNIT_REPRESENTATIVE = "unit_representative", "Unit Representative"
        SUPERVISOR = "supervisor", "Supervisor"
        MANAGER = "manager", "Manager"

    class MissingReason(models.TextChoices):
        CLIENT_ABSENT = "client_absent", "Client Absent"
        RESPONSIBLE_UNAVAILABLE = "responsible_unavailable", "Responsible Unavailable"
        REMOTE_SERVICE = "remote_service", "Remote Service"
        SIGNATURE_REFUSED = "signature_refused", "Signature Refused"
        SITE_CLOSED = "site_closed", "Site Closed"
        OTHER = "other", "Other"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    signature_type = models.CharField(max_length=40, choices=SignatureType.choices)
    signer_role = models.CharField(max_length=40, choices=SignerRole.choices)
    signer_name = models.CharField(max_length=180)
    signer_title = models.CharField(max_length=120, blank=True)
    signer_document = models.CharField(max_length=60, blank=True)
    signer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="service_signatures",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="service_signatures",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="service_signatures",
        null=True,
        blank=True,
    )
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.CASCADE,
        related_name="service_signatures",
        null=True,
        blank=True,
    )
    report_type = models.CharField(max_length=60, blank=True)
    report_reference_code = models.CharField(max_length=120, blank=True)
    checklist_execution_reference = models.CharField(max_length=120, blank=True)
    signed_at = models.DateTimeField(default=timezone.now)
    signature_data = models.TextField(blank=True)
    signature_format = models.CharField(max_length=30, default="data_url")
    acceptance_notes = models.TextField(blank=True)
    missing_reason = models.CharField(max_length=40, choices=MissingReason.choices, blank=True)
    missing_reason_notes = models.TextField(blank=True)
    signed_ip = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(max_length=80, blank=True)
    correlation_id = models.CharField(max_length=80, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_service_signatures"
        ordering = ["-signed_at", "-created_at"]
        indexes = [
            models.Index(fields=["signature_type", "is_current"], name="smart_sig_type_curr_idx"),
            models.Index(fields=["service_order", "signature_type"], name="smart_signature_order_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.signature_type} - {self.signer_name}"


class FieldExecutionSnapshot(models.Model):
    class SyncState(models.TextChoices):
        LOCAL_PENDING = "local_pending", "Local Pending"
        SYNCED = "synced", "Synced"
        CONFLICT = "conflict", "Conflict"
        ERROR = "error", "Error"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="field_execution_snapshots",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="field_execution_snapshots",
        null=True,
        blank=True,
    )
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.CASCADE,
        related_name="field_execution_snapshots",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="field_execution_snapshots",
        null=True,
        blank=True,
    )
    sync_state = models.CharField(max_length=20, choices=SyncState.choices, default=SyncState.LOCAL_PENDING)
    execution_status = models.CharField(max_length=40, blank=True)
    progress = models.PositiveIntegerField(default=0)
    checklist_payload = models.JSONField(default=dict, blank=True)
    diagnosis_payload = models.JSONField(default=dict, blank=True)
    executed_action_payload = models.JSONField(default=dict, blank=True)
    materials_payload = models.JSONField(default=list, blank=True)
    evidence_payload = models.JSONField(default=list, blank=True)
    finalization_payload = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_client_event_at = models.DateTimeField(null=True, blank=True)
    last_server_sync_at = models.DateTimeField(null=True, blank=True)
    last_client_operation_id = models.CharField(max_length=120, blank=True)
    last_conflict_code = models.CharField(max_length=80, blank=True)
    last_conflict_message = models.TextField(blank=True)
    local_device_id = models.CharField(max_length=120, blank=True)
    app_version = models.CharField(max_length=60, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_field_execution_snapshots"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_order", "technician"],
                name="uniq_smart_system_field_snapshot_order_technician",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service_order.order_number} - {self.sync_state}"


class FieldSyncOperation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        CONFLICT = "conflict", "Conflict"
        ERROR = "error", "Error"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="field_sync_operations",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="field_sync_operations",
        null=True,
        blank=True,
    )
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.CASCADE,
        related_name="field_sync_operations",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="field_sync_operations",
        null=True,
        blank=True,
    )
    client_operation_id = models.CharField(max_length=120, unique=True)
    action_type = models.CharField(max_length=60)
    operation_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    request_id = models.CharField(max_length=80, blank=True)
    correlation_id = models.CharField(max_length=80, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_field_sync_operations"
        ordering = ["status", "created_at"]
        indexes = [
            models.Index(fields=["service_order", "status"], name="smart_fsync_order_status_idx"),
            models.Index(fields=["technician", "created_at"], name="smart_fsync_tech_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.client_operation_id} - {self.status}"


class TechnicianAvailabilityWindow(models.Model):
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
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_availability_windows",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="technician_availability_windows",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technician_availability_windows",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.SET_NULL,
        related_name="availability_windows",
        null=True,
        blank=True,
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices, null=True, blank=True)
    blocked_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    max_daily_jobs = models.PositiveIntegerField(default=6)
    max_daily_hours = models.PositiveIntegerField(default=8)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_technician_availability_windows"
        ordering = ["technician_id", "weekday", "blocked_date", "start_time"]
        indexes = [
            models.Index(fields=["company", "technician"], name="smart_avail_comp_tech_idx"),
            models.Index(fields=["blocked_date", "is_available"], name="smart_availability_blocked_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.technician_id} availability"


class TechnicianSchedule(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_schedules",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="technician_schedules",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="smart_system_schedules",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.SET_NULL,
        related_name="smart_system_schedules",
        null=True,
        blank=True,
    )
    date = models.DateField(db_index=True)
    total_jobs = models.PositiveIntegerField(default=0)
    total_estimated_duration = models.PositiveIntegerField(default=0)
    total_estimated_travel = models.PositiveIntegerField(default=0)
    total_conflicts = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_technician_schedules"
        ordering = ["date", "technician_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "technician", "date"],
                name="uniq_smart_system_schedule_company_technician_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.technician_id} - {self.date}"


class RoutePlan(models.Model):
    class OptimizationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATED = "generated", "Generated"
        MANUAL = "manual", "Manual"
        NEEDS_REVIEW = "needs_review", "Needs Review"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="route_plans",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="route_plans",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="route_plans",
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.SET_NULL,
        related_name="route_plans",
        null=True,
        blank=True,
    )
    date = models.DateField(db_index=True)
    total_stops = models.PositiveIntegerField(default=0)
    total_estimated_duration = models.PositiveIntegerField(default=0)
    total_estimated_travel = models.PositiveIntegerField(default=0)
    optimization_status = models.CharField(
        max_length=20,
        choices=OptimizationStatus.choices,
        default=OptimizationStatus.DRAFT,
    )
    route_summary = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_route_plans"
        ordering = ["-date", "technician_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "technician", "date"],
                name="uniq_smart_system_route_plan_company_technician_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.technician_id} route {self.date}"


class ScheduledVisit(models.Model):
    class SourceType(models.TextChoices):
        WORK_ORDER = "work_order", "Work Order"
        PREVENTIVE = "preventive", "Preventive"
        MARKETPLACE = "marketplace", "Marketplace Assignment"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING_ASSIGNMENT = "pending_assignment", "Pending Assignment"
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="scheduled_visits",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    work_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    service_assignment = models.ForeignKey(
        "marketplace_technicians.TechnicianAssignment",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    maintenance_plan = models.ForeignKey(
        "smart_system.MaintenancePlan",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    technician_schedule = models.ForeignKey(
        "smart_system.TechnicianSchedule",
        on_delete=models.SET_NULL,
        related_name="visits",
        null=True,
        blank=True,
    )
    route_plan = models.ForeignKey(
        "smart_system.RoutePlan",
        on_delete=models.SET_NULL,
        related_name="visits",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    technician_profile = models.ForeignKey(
        "marketplace_technicians.TechnicianProfile",
        on_delete=models.SET_NULL,
        related_name="scheduled_visits",
        null=True,
        blank=True,
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.WORK_ORDER)
    title = models.CharField(max_length=180)
    scheduled_date = models.DateField(db_index=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    window_start = models.TimeField(null=True, blank=True)
    window_end = models.TimeField(null=True, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(default=60)
    estimated_travel_minutes = models.PositiveIntegerField(default=0)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_ASSIGNMENT)
    route_order = models.PositiveIntegerField(default=0)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    location_label = models.CharField(max_length=180, blank=True)
    conflict_flags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_scheduled_visits"
        ordering = ["scheduled_date", "route_order", "scheduled_start", "title"]
        indexes = [
            models.Index(fields=["company", "scheduled_date"], name="smart_visit_company_date_idx"),
            models.Index(fields=["technician", "scheduled_date"], name="smart_visit_tech_date_idx"),
            models.Index(fields=["status", "scheduled_date"], name="smart_visit_status_date_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ClientPortalRequest(models.Model):
    class Category(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance"
        INSPECTION = "inspection", "Inspection"
        REPORT = "report", "Report"
        ACCESS = "access", "Access"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    protocol_number = models.CharField(max_length=40, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="client_portal_requests",
    )
    operational_site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="client_portal_requests",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="client_portal_requests",
        null=True,
        blank=True,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="client_portal_requests",
        null=True,
        blank=True,
    )
    related_service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="client_portal_requests",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.MAINTENANCE)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    description = models.TextField()
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    desired_date = models.DateField(null=True, blank=True)
    last_customer_update_at = models.DateTimeField(default=timezone.now)
    internal_notes = models.TextField(blank=True)
    resolution_summary = models.TextField(blank=True)
    marketplace_request_reference = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "smart_system_client_portal_requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.protocol_number
