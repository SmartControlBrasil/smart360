import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class DecisionPolicy(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class TenantScopeMode(models.TextChoices):
        GLOBAL = "global", "Global"
        COMPANY = "company", "Company"
        SITE = "site", "Site"

    class AutonomyLevel(models.IntegerChoices):
        LEVEL_0 = 0, "Level 0 - Recommendation"
        LEVEL_1 = 1, "Level 1 - Human Approval"
        LEVEL_2 = 2, "Level 2 - Safe Auto Execution"
        LEVEL_3 = 3, "Level 3 - Expanded Autonomy"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    action_type = models.CharField(max_length=80, db_index=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)
    autonomy_level = models.PositiveSmallIntegerField(
        choices=AutonomyLevel.choices,
        default=AutonomyLevel.LEVEL_1,
    )
    requires_human_approval = models.BooleanField(default=True)
    enabled = models.BooleanField(default=True)
    tenant_scope_mode = models.CharField(
        max_length=20,
        choices=TenantScopeMode.choices,
        default=TenantScopeMode.COMPANY,
    )
    approver_role_slugs = models.JSONField(default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_decision_policies"
        ordering = ["action_type", "name"]

    def __str__(self) -> str:
        return self.name


class AgentDecision(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class TenantScopeMode(models.TextChoices):
        GLOBAL = "global", "Global"
        COMPANY = "company", "Company"
        SITE = "site", "Site"

    class DecisionStatus(models.TextChoices):
        PENDING_POLICY = "pending_policy", "Pending Policy"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        AUTO_APPROVED = "auto_approved", "Auto Approved"
        AUTO_BLOCKED = "auto_blocked", "Auto Blocked"
        ESCALATED = "escalated", "Escalated"
        EXECUTED = "executed", "Executed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agent_action_proposal = models.OneToOneField(
        "ai_agents_center.AgentActionProposal",
        on_delete=models.CASCADE,
        related_name="decision",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="agent_decisions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="agent_decisions",
        null=True,
        blank=True,
    )
    action_type = models.CharField(max_length=80, db_index=True)
    normalized_action_type = models.CharField(max_length=80, db_index=True)
    target_entity = models.CharField(max_length=80, blank=True, db_index=True)
    target_entity_id = models.CharField(max_length=120, blank=True, db_index=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.MEDIUM, db_index=True)
    autonomy_level = models.PositiveSmallIntegerField(default=1)
    tenant_scope_mode = models.CharField(
        max_length=20,
        choices=TenantScopeMode.choices,
        default=TenantScopeMode.COMPANY,
    )
    requires_human_approval = models.BooleanField(default=True)
    can_auto_execute = models.BooleanField(default=False)
    rollback_required = models.BooleanField(default=False)
    decision_status = models.CharField(
        max_length=30,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING_POLICY,
        db_index=True,
    )
    decision_reason = models.TextField(blank=True)
    policy_applied = models.ForeignKey(
        "ai_decision_engine.DecisionPolicy",
        on_delete=models.SET_NULL,
        related_name="decisions",
        null=True,
        blank=True,
    )
    decided_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_decisions_made",
        null=True,
        blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    explainability_payload = models.JSONField(default=dict, blank=True)
    execution_payload = models.JSONField(default=dict, blank=True)
    escalation_target = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agent_decisions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "decision_status"], name="ai_decision_company_status_idx"),
            models.Index(fields=["site", "decision_status"], name="ai_decision_site_status_idx"),
            models.Index(fields=["normalized_action_type", "risk_level"], name="ai_decision_action_risk_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.normalized_action_type} [{self.decision_status}]"


class DecisionApproval(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    decision = models.ForeignKey(
        "ai_decision_engine.AgentDecision",
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decision_approvals",
        null=True,
        blank=True,
    )
    requested_role_slugs = models.JSONField(default=list, blank=True)
    comment = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_decision_approvals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.decision_id} [{self.approval_status}]"


class DecisionExecution(models.Model):
    class ExecutionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    class ExecutedByMode(models.TextChoices):
        AUTO = "auto", "Auto"
        USER = "user", "User"
        SYSTEM = "system", "System"
        REPLAY = "replay", "Replay"

    class RollbackStatus(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not Required"
        AVAILABLE = "available", "Available"
        EXECUTED = "executed", "Executed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    decision = models.ForeignKey(
        "ai_decision_engine.AgentDecision",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING,
        db_index=True,
    )
    execution_summary = models.TextField(blank=True)
    executed_by_mode = models.CharField(
        max_length=20,
        choices=ExecutedByMode.choices,
        default=ExecutedByMode.SYSTEM,
    )
    executed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decision_executions",
        null=True,
        blank=True,
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    rollback_supported = models.BooleanField(default=False)
    rollback_status = models.CharField(
        max_length=20,
        choices=RollbackStatus.choices,
        default=RollbackStatus.NOT_REQUIRED,
    )
    rollback_reason = models.TextField(blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_decision_executions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.decision_id} [{self.execution_status}]"


class DecisionAuditTrail(models.Model):
    class ActorMode(models.TextChoices):
        SYSTEM = "system", "System"
        POLICY = "policy", "Policy"
        USER = "user", "User"
        HANDLER = "handler", "Handler"
        AGENT = "agent", "Agent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    decision = models.ForeignKey(
        "ai_decision_engine.AgentDecision",
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    event_type = models.CharField(max_length=80, db_index=True)
    actor_mode = models.CharField(max_length=20, choices=ActorMode.choices, default=ActorMode.SYSTEM)
    actor_label = models.CharField(max_length=160, blank=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decision_audit_entries",
        null=True,
        blank=True,
    )
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_decision_audit_trail"
        ordering = ["occurred_at", "id"]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.occurred_at.isoformat()}"


def _policy_seed_data():
    return [
        {
            "slug": "decision-create-work-order-proposal",
            "name": "Create Work Order Proposal",
            "description": "Ordens de servico derivadas de sinais dos agentes exigem aprovacao operacional.",
            "action_type": "create_work_order_proposal",
            "risk_level": DecisionPolicy.RiskLevel.HIGH,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["maintenance-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-create-preventive-review-task",
            "name": "Create Preventive Review Task",
            "description": "Revisoes preventivas permanecem aprovaveis por gestao de manutencao.",
            "action_type": "create_preventive_review_task",
            "risk_level": DecisionPolicy.RiskLevel.MEDIUM,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["maintenance-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-mark-asset-attention",
            "name": "Mark Asset Attention",
            "description": "Marcacao de watchlist e segura para autoexecucao sob policy explicita.",
            "action_type": "mark_asset_attention",
            "risk_level": DecisionPolicy.RiskLevel.LOW,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_2,
            "requires_human_approval": False,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["maintenance-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "auto"},
        },
        {
            "slug": "decision-create-schedule-adjustment-proposal",
            "name": "Create Schedule Adjustment Proposal",
            "description": "Mudancas de agenda ficam aprovaveis por coordenacao operacional.",
            "action_type": "create_schedule_adjustment_proposal",
            "risk_level": DecisionPolicy.RiskLevel.HIGH,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["coordinator", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-reorder-route-proposal",
            "name": "Reorder Route Proposal",
            "description": "Reordenacao de rota continua human-in-the-loop nesta rodada.",
            "action_type": "reorder_route_proposal",
            "risk_level": DecisionPolicy.RiskLevel.MEDIUM,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["coordinator", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-assign-marketplace-candidate-proposal",
            "name": "Assign Marketplace Candidate Proposal",
            "description": "Alocacoes de marketplace continuam aprovaveis por coordenacao.",
            "action_type": "assign_marketplace_candidate_proposal",
            "risk_level": DecisionPolicy.RiskLevel.HIGH,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.COMPANY,
            "approver_role_slugs": ["coordinator", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-flag-contract-profitability-attention",
            "name": "Flag Contract Profitability Attention",
            "description": "Flags de rentabilidade sao registradas com seguranca; contratos criticos sobem para escalonamento.",
            "action_type": "flag_contract_profitability_attention",
            "risk_level": DecisionPolicy.RiskLevel.MEDIUM,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_2,
            "requires_human_approval": False,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.COMPANY,
            "approver_role_slugs": ["commercial-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "auto", "critical_requires_escalation": True},
        },
        {
            "slug": "decision-create-investigation-task",
            "name": "Create Investigation Task",
            "description": "Investigacoes internas podem ser materializadas automaticamente quando nao destrutivas.",
            "action_type": "create_investigation_task",
            "risk_level": DecisionPolicy.RiskLevel.LOW,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_2,
            "requires_human_approval": False,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["maintenance-manager", "coordinator", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "auto"},
        },
        {
            "slug": "decision-escalate-operational-alert",
            "name": "Escalate Operational Alert",
            "description": "Escalonamentos permanecem auditados e com aprovacao quando houver impacto critico.",
            "action_type": "escalate_operational_alert",
            "risk_level": DecisionPolicy.RiskLevel.MEDIUM,
            "autonomy_level": DecisionPolicy.AutonomyLevel.LEVEL_1,
            "requires_human_approval": True,
            "tenant_scope_mode": DecisionPolicy.TenantScopeMode.SITE,
            "approver_role_slugs": ["coordinator", "maintenance-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
    ]


