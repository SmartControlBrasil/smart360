import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class AgentDefinition(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        ARCHIVED = "archived", "Archived"

    class Domain(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance"
        SCHEDULING = "scheduling", "Scheduling"
        PROFITABILITY = "profitability", "Profitability"
        MARKETPLACE = "marketplace", "Marketplace"
        ANOMALY = "anomaly", "Anomaly"
        PLATFORM = "platform", "Platform"

    class AutonomyLevel(models.IntegerChoices):
        PASSIVE = 0, "Level 0 - Passive"
        RECOMMEND = 1, "Level 1 - Recommendation"
        PROPOSE = 2, "Level 2 - Proposal"
        AUTO_EXECUTE = 3, "Level 3 - Auto Execute"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    domain = models.CharField(max_length=40, choices=Domain.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    autonomy_level = models.PositiveSmallIntegerField(
        choices=AutonomyLevel.choices,
        default=AutonomyLevel.RECOMMEND,
    )
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_definitions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AgentExecutionPolicy(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.OneToOneField(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="execution_policy",
    )
    require_human_approval = models.BooleanField(default=True)
    allow_manual_runs = models.BooleanField(default=True)
    allow_scheduled_runs = models.BooleanField(default=True)
    enforce_billing_active = models.BooleanField(default=True)
    allowed_tools = models.JSONField(default=list, blank=True)
    allowed_action_types = models.JSONField(default=list, blank=True)
    max_recommendations = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_execution_policies"
        ordering = ["agent__name"]

    def __str__(self):
        return f"Policy for {self.agent}"


class AgentRun(models.Model):
    class TriggerType(models.TextChoices):
        MANUAL = "manual", "Manual"
        EVENT = "event", "Event"
        SCHEDULED = "scheduled", "Scheduled"
        API = "api", "API"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="runs",
    )
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, db_index=True)
    trigger_reference = models.CharField(max_length=180, blank=True, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_runs",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_runs",
        null=True,
        blank=True,
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="triggered_agent_runs",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    input_context = models.JSONField(default=dict, blank=True)
    output_summary = models.TextField(blank=True)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_runs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agent.slug} [{self.status}]"


class AgentRecommendation(models.Model):
    class RecommendationType(models.TextChoices):
        INSIGHT = "insight", "Insight"
        PREVENTIVE = "preventive", "Preventive"
        REBALANCING = "rebalancing", "Rebalancing"
        PROFITABILITY = "profitability", "Profitability"
        MARKETPLACE = "marketplace", "Marketplace"
        ANOMALY = "anomaly", "Anomaly"
        PREVENTIVE_REVIEW = "preventive_review", "Preventive Review"
        EXTRAORDINARY_INSPECTION = "extraordinary_inspection", "Extraordinary Inspection"
        FAILURE_PATTERN_ALERT = "failure_pattern_alert", "Failure Pattern Alert"
        RELIABILITY_ATTENTION = "reliability_attention", "Reliability Attention"
        ACTION_PLAN_RECOMMENDATION = "action_plan_recommendation", "Action Plan Recommendation"
        CRITICAL_ASSET_WATCH = "critical_asset_watch", "Critical Asset Watch"
        TECHNICIAN_OVERLOAD = "technician_overload", "Technician Overload"
        ROUTE_REORDER = "route_reorder", "Route Reorder"
        VISIT_REASSIGNMENT = "visit_reassignment", "Visit Reassignment"
        SLA_RISK_ALERT = "sla_risk_alert", "SLA Risk Alert"
        UNASSIGNED_VISIT_ATTENTION = "unassigned_visit_attention", "Unassigned Visit Attention"
        IDLE_CAPACITY_OPPORTUNITY = "idle_capacity_opportunity", "Idle Capacity Opportunity"
        ROUTE_EFFICIENCY_ATTENTION = "route_efficiency_attention", "Route Efficiency Attention"
        CLIENT_MARGIN_ALERT = "client_margin_alert", "Client Margin Alert"
        CONTRACT_PROFITABILITY_RISK = "contract_profitability_risk", "Contract Profitability Risk"
        EXCESSIVE_SERVICE_COST = "excessive_service_cost", "Excessive Service Cost"
        ROUTE_MARGIN_EROSION = "route_margin_erosion", "Route Margin Erosion"
        TECHNICIAN_EFFICIENCY_ATTENTION = "technician_efficiency_attention", "Technician Efficiency Attention"
        REPRICING_RECOMMENDATION = "repricing_recommendation", "Repricing Recommendation"
        SCOPE_REVIEW_RECOMMENDATION = "scope_review_recommendation", "Scope Review Recommendation"
        PROFITABILITY_WATCH = "profitability_watch", "Profitability Watch"
        TECHNICIAN_ALLOCATION_RECOMMENDATION = "technician_allocation_recommendation", "Technician Allocation Recommendation"
        NO_VIABLE_CANDIDATE_ALERT = "no_viable_candidate_alert", "No Viable Candidate Alert"
        SLA_ALLOCATION_RISK = "sla_allocation_risk", "SLA Allocation Risk"
        FALLBACK_ASSIGNMENT_RECOMMENDATION = "fallback_assignment_recommendation", "Fallback Assignment Recommendation"
        TECHNICIAN_UNAVAILABLE_CONFLICT = "technician_unavailable_conflict", "Technician Unavailable Conflict"
        MARKETPLACE_REQUEST_ATTENTION = "marketplace_request_attention", "Marketplace Request Attention"
        ANOMALY_FAILURE_SPIKE = "anomaly_failure_spike", "Anomaly Failure Spike"
        ANOMALY_BACKLOG_GROWTH = "anomaly_backlog_growth", "Anomaly Backlog Growth"
        ANOMALY_SLA_DROP = "anomaly_sla_drop", "Anomaly SLA Drop"
        ANOMALY_PARTS_CONSUMPTION = "anomaly_parts_consumption", "Anomaly Parts Consumption"
        ANOMALY_TECHNICIAN_BEHAVIOR = "anomaly_technician_behavior", "Anomaly Technician Behavior"
        ANOMALY_MARKETPLACE_SIGNAL = "anomaly_marketplace_signal", "Anomaly Marketplace Signal"
        ANOMALY_CONTRACT_MARGIN_SHIFT = "anomaly_contract_margin_shift", "Anomaly Contract Margin Shift"
        ANOMALY_SITE_RISK_ALERT = "anomaly_site_risk_alert", "Anomaly Site Risk Alert"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        IMMEDIATE = "immediate", "Immediate"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWED = "reviewed", "Reviewed"
        ACCEPTED = "accepted", "Accepted"
        DISMISSED = "dismissed", "Dismissed"
        APPLIED = "applied", "Applied"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_recommendations",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_recommendations",
        null=True,
        blank=True,
    )
    recommendation_type = models.CharField(
    max_length=50,  # ou 64 pra ficar tranquilo
    choices=RecommendationType.choices
)
    title = models.CharField(max_length=240)
    summary = models.TextField()
    explanation = models.TextField(blank=True)
    evidence_summary = models.TextField(blank=True)
    suggested_action = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0)
    requires_human_approval = models.BooleanField(default=True)
    entity_type = models.CharField(max_length=80, blank=True, db_index=True)
    entity_id = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_recommendations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AgentActionProposal(models.Model):
    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXECUTED = "executed", "Executed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.CASCADE,
        related_name="action_proposals",
    )
    action_type = models.CharField(max_length=80, db_index=True)
    target_entity = models.CharField(max_length=80, blank=True, db_index=True)
    target_entity_id = models.CharField(max_length=120, blank=True, db_index=True)
    title = models.CharField(max_length=240, blank=True)
    summary = models.TextField(blank=True)
    proposed_payload = models.JSONField(default=dict, blank=True)
    priority = models.CharField(max_length=20, default="medium", db_index=True)
    approval_required = models.BooleanField(default=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_APPROVAL, db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_agent_action_proposals",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="rejected_agent_action_proposals",
        null=True,
        blank=True,
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_action_proposals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action_type} [{self.status}]"


class AgentAssetAttentionFlag(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WATCHING = "watching", "Watching"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="asset_attention_flags",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_asset_attention_flags",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_asset_attention_flags",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.CASCADE,
        related_name="agent_attention_flags",
    )
    latest_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="asset_attention_flags",
        null=True,
        blank=True,
    )
    latest_recommendation = models.ForeignKey(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.SET_NULL,
        related_name="asset_attention_flags",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    summary = models.CharField(max_length=240)
    risk_level = models.CharField(max_length=20, default="medium", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_asset_attention_flags"
        ordering = ["-attention_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "asset"],
                name="uniq_ai_agents_asset_attention_flag",
            ),
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} [{self.risk_level}]"


class AgentScheduleHealthFlag(models.Model):
    class FlagType(models.TextChoices):
        TECHNICIAN_OVERLOAD = "technician_overload", "Technician Overload"
        CONFLICT = "conflict", "Conflict"
        SLA_RISK = "sla_risk", "SLA Risk"
        UNASSIGNED_BACKLOG = "unassigned_backlog", "Unassigned Backlog"
        IDLE_CAPACITY = "idle_capacity", "Idle Capacity"
        ROUTE_EFFICIENCY = "route_efficiency", "Route Efficiency"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WATCHING = "watching", "Watching"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="schedule_health_flags",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_schedule_health_flags",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_schedule_health_flags",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="agent_schedule_health_flags",
        null=True,
        blank=True,
    )
    schedule_date = models.DateField(db_index=True, null=True, blank=True)
    flag_type = models.CharField(max_length=40, choices=FlagType.choices, db_index=True)
    latest_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="schedule_health_flags",
        null=True,
        blank=True,
    )
    latest_recommendation = models.ForeignKey(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.SET_NULL,
        related_name="schedule_health_flags",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    summary = models.CharField(max_length=240)
    risk_level = models.CharField(max_length=20, default="medium", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_schedule_health_flags"
        ordering = ["-attention_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "technician", "schedule_date", "flag_type"],
                name="uniq_ai_agents_schedule_health_flag",
            ),
        ]

    def __str__(self):
        return f"{self.flag_type} [{self.schedule_date}]"


class AgentProfitabilityAttentionFlag(models.Model):
    class FocusType(models.TextChoices):
        CLIENT = "client", "Client"
        CONTRACT = "contract", "Contract"
        TECHNICIAN = "technician", "Technician"
        SITE = "site", "Site"
        WORK_ORDER = "work_order", "Work Order"
        ROUTE = "route", "Route"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WATCHING = "watching", "Watching"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="profitability_attention_flags",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_profitability_attention_flags",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_profitability_attention_flags",
        null=True,
        blank=True,
    )
    client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.SET_NULL,
        related_name="agent_profitability_attention_flags",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.SET_NULL,
        related_name="agent_profitability_attention_flags",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="agent_profitability_attention_flags",
        null=True,
        blank=True,
    )
    focus_type = models.CharField(max_length=30, choices=FocusType.choices, db_index=True)
    target_entity_type = models.CharField(max_length=80, db_index=True)
    target_entity_id = models.CharField(max_length=120, db_index=True)
    display_label = models.CharField(max_length=240)
    latest_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="profitability_attention_flags",
        null=True,
        blank=True,
    )
    latest_recommendation = models.ForeignKey(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.SET_NULL,
        related_name="profitability_attention_flags",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    summary = models.CharField(max_length=240)
    risk_level = models.CharField(max_length=20, default="medium", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_profitability_attention_flags"
        ordering = ["-attention_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "focus_type", "target_entity_type", "target_entity_id"],
                name="uniq_ai_agents_profitability_attention_flag",
            ),
        ]

    def __str__(self):
        return f"{self.display_label} [{self.focus_type}]"


class AgentMarketplaceRequestFlag(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WATCHING = "watching", "Watching"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="marketplace_request_flags",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_marketplace_request_flags",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_marketplace_request_flags",
        null=True,
        blank=True,
    )
    service_request = models.ForeignKey(
        "marketplace_technicians.TechnicianServiceRequest",
        on_delete=models.CASCADE,
        related_name="agent_marketplace_request_flags",
    )
    latest_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="marketplace_request_flags",
        null=True,
        blank=True,
    )
    latest_recommendation = models.ForeignKey(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.SET_NULL,
        related_name="marketplace_request_flags",
        null=True,
        blank=True,
    )
    best_candidate_profile_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    summary = models.CharField(max_length=240)
    risk_level = models.CharField(max_length=20, default="medium", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_marketplace_request_flags"
        ordering = ["-attention_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "service_request"],
                name="uniq_ai_agents_marketplace_request_flag",
            ),
        ]

    def __str__(self):
        return f"{self.service_request.title} [{self.risk_level}]"


class AgentAnomalyAttentionFlag(models.Model):
    class FocusType(models.TextChoices):
        ASSET = "asset", "Asset"
        SITE = "site", "Site"
        TECHNICIAN = "technician", "Technician"
        CLIENT = "client", "Client"
        CONTRACT = "contract", "Contract"
        PART = "part", "Part"
        MARKETPLACE = "marketplace", "Marketplace"
        COMPANY = "company", "Company"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WATCHING = "watching", "Watching"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="anomaly_attention_flags",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_anomaly_attention_flags",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "smart_system.Asset",
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    client = models.ForeignKey(
        "smart_system.MaintenanceClient",
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "smart_system.MaintenanceContract",
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    part = models.ForeignKey(
        "smart_system.Part",
        on_delete=models.SET_NULL,
        related_name="agent_anomaly_attention_flags",
        null=True,
        blank=True,
    )
    focus_type = models.CharField(max_length=30, choices=FocusType.choices, db_index=True)
    target_entity_type = models.CharField(max_length=80, db_index=True)
    target_entity_id = models.CharField(max_length=120, db_index=True)
    display_label = models.CharField(max_length=240)
    latest_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="anomaly_attention_flags",
        null=True,
        blank=True,
    )
    latest_recommendation = models.ForeignKey(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.SET_NULL,
        related_name="anomaly_attention_flags",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    attention_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    summary = models.CharField(max_length=240)
    risk_level = models.CharField(max_length=20, default="medium", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    last_detected_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_anomaly_attention_flags"
        ordering = ["-attention_score", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "company", "focus_type", "target_entity_type", "target_entity_id"],
                name="uniq_ai_agents_anomaly_attention_flag",
            ),
        ]

    def __str__(self):
        return f"{self.display_label} [{self.focus_type}]"


class AgentMemoryEntry(models.Model):
    class MemoryKind(models.TextChoices):
        ENTITY_SUMMARY = "entity_summary", "Entity Summary"
        TENANT_CONTEXT = "tenant_context", "Tenant Context"
        ANALYTICS_SNAPSHOT = "analytics_snapshot", "Analytics Snapshot"
        OPERATIONS_SUMMARY = "operations_summary", "Operations Summary"
        RECOMMENDATION_FEEDBACK = "recommendation_feedback", "Recommendation Feedback"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent = models.ForeignKey(
        "ai_agents_center.AgentDefinition",
        on_delete=models.CASCADE,
        related_name="memory_entries",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_memory_entries",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_memory_entries",
        null=True,
        blank=True,
    )
    entity_type = models.CharField(max_length=80, blank=True, db_index=True)
    entity_id = models.CharField(max_length=120, blank=True, db_index=True)
    memory_kind = models.CharField(max_length=40, choices=MemoryKind.choices, db_index=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_memory_entries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agent.slug}:{self.memory_kind}"


class CommercialOpportunity(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        ENRICHING = "enriching", "Enriching"
        READY_FOR_REVIEW = "ready_for_review", "Ready for Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CONVERTED_TO_LEAD = "converted_to_lead", "Converted to Lead"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        WEBSITE = "website", "Website"
        LINKEDIN = "linkedin", "LinkedIn"
        INSTAGRAM = "instagram", "Instagram"
        GOOGLE_MAPS = "google_maps", "Google Maps"
        PARTNER = "partner", "Partner"
        EVENT = "event", "Event"
        PUBLIC_DATA = "public_data", "Public Data"
        CSV = "csv", "CSV"

    class OutreachChannel(models.TextChoices):
        NONE = "none", "None"
        EMAIL = "email", "Email"

    class OutreachStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent_run = models.ForeignKey(
        "ai_agents_center.AgentRun",
        on_delete=models.SET_NULL,
        related_name="commercial_opportunities",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="commercial_opportunities",
        null=True,
        blank=True,
    )
    lead = models.ForeignKey(
        "growth_engine.Lead",
        on_delete=models.SET_NULL,
        related_name="commercial_opportunities",
        null=True,
        blank=True,
    )
    company_name = models.CharField(max_length=180)
    segment = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUAL, db_index=True)
    title = models.CharField(max_length=240)
    problem_detected = models.TextField()
    opportunity_description = models.TextField(blank=True)
    recommended_solution = models.TextField(blank=True)
    recommended_product = models.CharField(max_length=240, blank=True)
    commercial_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=0, db_index=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_commercial_opportunities",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="converted_commercial_opportunities",
        null=True,
        blank=True,
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    outreach_channel = models.CharField(
        max_length=30,
        choices=OutreachChannel.choices,
        default=OutreachChannel.NONE,
        db_index=True,
    )
    outreach_sender_email = models.CharField(max_length=254, blank=True, default="")
    outreach_domain = models.CharField(max_length=120, blank=True, default="")
    outreach_status = models.CharField(
        max_length=30,
        choices=OutreachStatus.choices,
        default=OutreachStatus.NOT_STARTED,
        db_index=True,
    )
    outreach_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_commercial_opportunities"
        ordering = ["-commercial_score", "-confidence_score", "-created_at"]
        indexes = [
            models.Index(fields=["status", "commercial_score"], name="ai_comm_opp_status_score_idx"),
            models.Index(fields=["source", "created_at"], name="ai_comm_opp_source_created_idx"),
        ]

    def __str__(self):
        return f"{self.company_name}: {self.title}"


class AtlasProspectImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="atlas_prospect_import_batches",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="atlas_prospect_import_batches",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=30, default=CommercialOpportunity.Source.MANUAL, db_index=True)
    filename = models.CharField(max_length=255, blank=True, default="")
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    created_opportunities = models.PositiveIntegerField(default=0)
    skipped_duplicates = models.PositiveIntegerField(default=0)
    skipped_empty_rows = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_atlas_prospect_import_batches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="ai_atl_imp_stat_crt_idx"),
            models.Index(fields=["source", "created_at"], name="ai_atl_imp_src_crt_idx"),
        ]

    def __str__(self):
        label = self.filename or self.source
        return f"Atlas import {label} ({self.status})"


class ManagerCopilotConfiguration(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="manager_copilot_configurations",
        null=True,
        blank=True,
    )
    is_enabled = models.BooleanField(default=True)
    default_suggestions = models.JSONField(default=list, blank=True)
    behavior_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_manager_copilot_configurations"
        ordering = ["company__name", "created_at"]

    def __str__(self):
        return getattr(self.company, "name", "Global Copilot")


class ManagerCopilotSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESET = "reset", "Reset"
        CLOSED = "closed", "Closed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="manager_copilot_sessions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="manager_copilot_sessions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="manager_copilot_sessions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    title = models.CharField(max_length=180, blank=True)
    current_context = models.JSONField(default=dict, blank=True)
    last_intent = models.CharField(max_length=60, blank=True, db_index=True)
    last_query = models.TextField(blank=True)
    message_count = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_manager_copilot_sessions"
        ordering = ["-last_activity_at", "-created_at"]

    def __str__(self):
        return self.title or f"Copilot session {self.public_id}"


class ManagerCopilotMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    session = models.ForeignKey(
        "ai_agents_center.ManagerCopilotSession",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    content = models.TextField(blank=True)
    detected_intent = models.CharField(max_length=60, blank=True, db_index=True)
    context_snapshot = models.JSONField(default=dict, blank=True)
    referenced_agents = models.JSONField(default=list, blank=True)
    structured_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_manager_copilot_messages"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.session_id}:{self.role}"


class TechnicianCopilotConfiguration(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_copilot_configurations",
        null=True,
        blank=True,
    )
    is_enabled = models.BooleanField(default=True)
    allow_offline_fallback = models.BooleanField(default=True)
    default_suggestions = models.JSONField(default=list, blank=True)
    behavior_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_technician_copilot_configurations"
        ordering = ["company__name", "created_at"]

    def __str__(self):
        return getattr(self.company, "name", "Global Technician Copilot")


class TechnicianCopilotSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        OFFLINE = "offline", "Offline"
        CLOSED = "closed", "Closed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technician_copilot_sessions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_copilot_sessions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="technician_copilot_sessions",
        null=True,
        blank=True,
    )
    service_order = models.ForeignKey(
        "smart_system.ServiceOrder",
        on_delete=models.SET_NULL,
        related_name="technician_copilot_sessions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    current_context = models.JSONField(default=dict, blank=True)
    last_intent = models.CharField(max_length=60, blank=True, db_index=True)
    message_count = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_technician_copilot_sessions"
        ordering = ["-last_activity_at", "-created_at"]

    def __str__(self):
        return f"Tech copilot {self.public_id}"


class TechnicianCopilotMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    session = models.ForeignKey(
        "ai_agents_center.TechnicianCopilotSession",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    content = models.TextField(blank=True)
    detected_intent = models.CharField(max_length=60, blank=True, db_index=True)
    was_offline = models.BooleanField(default=False)
    context_snapshot = models.JSONField(default=dict, blank=True)
    structured_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_technician_copilot_messages"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.session_id}:{self.role}"


class ClientPortalCopilotConfiguration(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="client_portal_copilot_configurations",
        null=True,
        blank=True,
    )
    is_enabled = models.BooleanField(default=True)
    default_suggestions = models.JSONField(default=list, blank=True)
    behavior_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_client_portal_copilot_configurations"
        ordering = ["company__name", "created_at"]

    def __str__(self):
        return getattr(self.company, "name", "Global Client Portal Copilot")


class ClientPortalCopilotSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESET = "reset", "Reset"
        CLOSED = "closed", "Closed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_portal_copilot_sessions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="client_portal_copilot_sessions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="client_portal_copilot_sessions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    title = models.CharField(max_length=180, blank=True)
    current_context = models.JSONField(default=dict, blank=True)
    last_intent = models.CharField(max_length=60, blank=True, db_index=True)
    last_query = models.TextField(blank=True)
    message_count = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_client_portal_copilot_sessions"
        ordering = ["-last_activity_at", "-created_at"]

    def __str__(self):
        return self.title or f"Client portal copilot {self.public_id}"


class ClientPortalCopilotMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    session = models.ForeignKey(
        "ai_agents_center.ClientPortalCopilotSession",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    content = models.TextField(blank=True)
    detected_intent = models.CharField(max_length=60, blank=True, db_index=True)
    context_snapshot = models.JSONField(default=dict, blank=True)
    structured_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_client_portal_copilot_messages"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.session_id}:{self.role}"


class AIBriefingConfiguration(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_briefing_configurations",
        null=True,
        blank=True,
    )
    is_enabled = models.BooleanField(default=True)
    delivery_channels = models.JSONField(default=list, blank=True)
    default_schedule = models.JSONField(default=dict, blank=True)
    behavior_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_briefing_configurations"
        ordering = ["company__name", "created_at"]

    def __str__(self):
        return getattr(self.company, "name", "Global AI Briefings")


class AIBriefing(models.Model):
    class BriefingType(models.TextChoices):
        DAILY_EXECUTIVE = "daily_executive", "Daily Executive Briefing"
        DAILY_FIELD = "daily_field", "Daily Field Briefing"
        DAILY_CLIENT = "daily_client", "Daily Client Briefing"
        WEEKLY_EXECUTIVE = "weekly_executive", "Weekly Executive Summary"
        ON_DEMAND = "on_demand", "On-demand Briefing"

    class Audience(models.TextChoices):
        MANAGER = "manager", "Manager"
        TECHNICIAN = "technician", "Technician"
        CLIENT = "client", "Client"

    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        DELIVERED = "delivered", "Delivered"
        VIEWED = "viewed", "Viewed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    briefing_type = models.CharField(max_length=40, choices=BriefingType.choices, db_index=True)
    audience = models.CharField(max_length=20, choices=Audience.choices, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ai_briefings",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="ai_briefings",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_briefings",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    period_label = models.CharField(max_length=120, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    content = models.JSONField(default=dict, blank=True)
    source_agents = models.JSONField(default=list, blank=True)
    source_recommendation_ids = models.JSONField(default=list, blank=True)
    source_proposal_ids = models.JSONField(default=list, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED, db_index=True)
    generated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_briefings"
        ordering = ["-generated_at", "-created_at"]

    def __str__(self):
        return self.title


class AIBriefingDelivery(models.Model):
    class Channel(models.TextChoices):
        DASHBOARD = "dashboard", "Dashboard"
        PORTAL = "portal", "Portal"
        FIELD_APP = "field_app", "Field App"
        IN_APP = "in_app", "In App"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        VIEWED = "viewed", "Viewed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    briefing = models.ForeignKey(
        "ai_agents_center.AIBriefing",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_briefing_deliveries",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_briefing_deliveries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.briefing_id}:{self.channel}"


class AtlasLead(models.Model):
    """
    DEPRECATED: modelo bruto do fluxo AtlasLead/PendingAtlasLead legado.

    O fluxo oficial do Atlas usa CommercialOpportunity:
    PoC/CSV/API -> import-prospects -> CommercialOpportunity -> revisão humana
    -> convert_to_lead -> Growth Engine Lead.

    Este modelo permanece apenas para compatibilidade e consulta de dados antigos.
    Não usar em novos fluxos de ingestão ou revisão.
    """
    class Segment(models.TextChoices):
        ESCOLA = "Escola / Educação", "Escola / Educação"
        LIMPEZA = "Limpeza / Facilities", "Limpeza / Facilities"
        SHOPPING = "Shopping / Clínica / Hotel", "Shopping / Clínica / Hotel"
        SEGURANCA = "Segurança / Indústria", "Segurança / Indústria"
        OUTROS = "Outros", "Outros"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Dados da Empresa
    razao_social = models.CharField(max_length=255)
    segmento = models.CharField(max_length=50, choices=Segment.choices, default=Segment.OUTROS)
    cidade = models.CharField(max_length=150, blank=True)
    regiao = models.CharField(max_length=150, blank=True)
    
    # Inteligência Comercial
    fit_comercial = models.CharField(max_length=50, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    
    # Decisor
    nome_decisor = models.CharField(max_length=255, blank=True, null=True)
    cargo_decisor = models.CharField(max_length=255, blank=True, null=True)
    email_contato = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=50, blank=True, null=True)
    
    # Status e Observações
    status = models.CharField(max_length=50, default="ready_for_review")
    notas = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents_atlas_leads"
        ordering = ["-score", "-created_at"]

    def __str__(self):
        return f"{self.razao_social} [{self.score}]"


class PendingAtlasLead(AtlasLead):
    """
    DEPRECATED: proxy do fluxo legado AtlasLead/PendingAtlasLead.

    Mantido apenas para compatibilidade operacional com registros antigos no
    Django Admin. Novas revisões Atlas devem usar CommercialOpportunity.
    """
    class Meta:
        proxy = True
        verbose_name = "Lead Pendente do Atlas"
        verbose_name_plural = "Leads Pendentes do Atlas"
