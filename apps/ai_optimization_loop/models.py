import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class EffectivenessLevel(models.TextChoices):
    VERY_EFFECTIVE = "very_effective", "Very Effective"
    EFFECTIVE = "effective", "Effective"
    NEUTRAL = "neutral", "Neutral"
    WEAK = "weak", "Weak"
    HARMFUL = "harmful", "Harmful"


class RecommendationOutcome(models.Model):
    class OutcomeStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        OBSERVED = "observed", "Observed"
        DISMISSED = "dismissed", "Dismissed"
        APPLIED = "applied", "Applied"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    recommendation = models.OneToOneField(
        "ai_agents_center.AgentRecommendation",
        on_delete=models.CASCADE,
        related_name="optimization_outcome",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="optimization_recommendation_outcomes",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="optimization_recommendation_outcomes",
        null=True,
        blank=True,
    )
    outcome_status = models.CharField(max_length=20, choices=OutcomeStatus.choices, default=OutcomeStatus.PENDING, db_index=True)
    expected_effect_summary = models.TextField(blank=True)
    observed_effect_summary = models.TextField(blank=True)
    effectiveness_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    effectiveness_level = models.CharField(max_length=20, choices=EffectivenessLevel.choices, default=EffectivenessLevel.NEUTRAL, db_index=True)
    comparison_payload = models.JSONField(default=dict, blank=True)
    measured_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_recommendation_outcomes"
        ordering = ["-measured_at", "-created_at"]


class DecisionOutcome(models.Model):
    class ResultStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REVERTED = "reverted", "Reverted"
        PARTIAL = "partial", "Partial"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    decision = models.OneToOneField(
        "ai_decision_engine.AgentDecision",
        on_delete=models.CASCADE,
        related_name="optimization_outcome",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="optimization_decision_outcomes",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="optimization_decision_outcomes",
        null=True,
        blank=True,
    )
    execution_status = models.CharField(max_length=20, blank=True, db_index=True)
    result_status = models.CharField(max_length=20, choices=ResultStatus.choices, default=ResultStatus.PENDING, db_index=True)
    expected_result = models.JSONField(default=dict, blank=True)
    actual_result = models.JSONField(default=dict, blank=True)
    effectiveness_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    effectiveness_level = models.CharField(max_length=20, choices=EffectivenessLevel.choices, default=EffectivenessLevel.NEUTRAL, db_index=True)
    evaluation_summary = models.TextField(blank=True)
    measured_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_decision_outcomes"
        ordering = ["-measured_at", "-created_at"]


class SimulationOutcome(models.Model):
    class ResultStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        OBSERVED = "observed", "Observed"
        NOT_EXECUTED = "not_executed", "Not Executed"
        DIVERGED = "diverged", "Diverged"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    simulation_run = models.OneToOneField(
        "ai_simulation_engine.SimulationRun",
        on_delete=models.CASCADE,
        related_name="optimization_outcome",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="optimization_simulation_outcomes",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="optimization_simulation_outcomes",
        null=True,
        blank=True,
    )
    result_status = models.CharField(max_length=20, choices=ResultStatus.choices, default=ResultStatus.PENDING, db_index=True)
    expected_result = models.JSONField(default=dict, blank=True)
    actual_result = models.JSONField(default=dict, blank=True)
    effectiveness_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    effectiveness_level = models.CharField(max_length=20, choices=EffectivenessLevel.choices, default=EffectivenessLevel.NEUTRAL, db_index=True)
    evaluation_summary = models.TextField(blank=True)
    measured_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_simulation_outcomes"
        ordering = ["-measured_at", "-created_at"]


class FeedbackSignal(models.Model):
    class SourceType(models.TextChoices):
        RECOMMENDATION = "recommendation", "Recommendation"
        DECISION = "decision", "Decision"
        SIMULATION = "simulation", "Simulation"
        COPILOT_MESSAGE = "copilot_message", "Copilot Message"
        AGENT = "agent", "Agent"

    class SignalType(models.TextChoices):
        USEFULNESS = "usefulness", "Usefulness"
        QUALITY = "quality", "Quality"
        OUTCOME = "outcome", "Outcome"
        CONFIDENCE = "confidence", "Confidence"
        ADOPTION = "adoption", "Adoption"
        IMPLICIT_OPERATIONAL = "implicit_operational", "Implicit Operational"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_type = models.CharField(max_length=30, choices=SourceType.choices, db_index=True)
    source_reference = models.CharField(max_length=120, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="optimization_feedback_signals",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="optimization_feedback_signals",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="optimization_feedback_signals",
        null=True,
        blank=True,
    )
    signal_type = models.CharField(max_length=30, choices=SignalType.choices, db_index=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    comment = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_feedback_signals"
        ordering = ["-created_at"]


class OptimizationPolicy(models.Model):
    class TargetType(models.TextChoices):
        AGENT_EXECUTION_POLICY = "agent_execution_policy", "Agent Execution Policy"
        DECISION_POLICY = "decision_policy", "Decision Policy"
        SIMULATION_TYPE = "simulation_type", "Simulation Type"
        COPILOT_CONFIGURATION = "copilot_configuration", "Copilot Configuration"

    class ProposalType(models.TextChoices):
        WEIGHT_ADJUSTMENT = "weight_adjustment", "Weight Adjustment"
        THRESHOLD_ADJUSTMENT = "threshold_adjustment", "Threshold Adjustment"
        POLICY_MODE_ADJUSTMENT = "policy_mode_adjustment", "Policy Mode Adjustment"
        APPROVAL_REQUIREMENT_ADJUSTMENT = "approval_requirement_adjustment", "Approval Requirement Adjustment"
        RANKING_ADJUSTMENT = "ranking_adjustment", "Ranking Adjustment"
        HEURISTIC_CONFIG_ADJUSTMENT = "heuristic_config_adjustment", "Heuristic Config Adjustment"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    target_type = models.CharField(max_length=40, choices=TargetType.choices, db_index=True)
    proposal_type = models.CharField(max_length=40, choices=ProposalType.choices, db_index=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)
    requires_human_approval = models.BooleanField(default=True)
    auto_apply_on_approval = models.BooleanField(default=False)
    approver_role_slugs = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_policies"
        ordering = ["target_type", "proposal_type", "slug"]


class OptimizationProposal(models.Model):
    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    class AppliedByMode(models.TextChoices):
        USER = "user", "User"
        SYSTEM = "system", "System"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="optimization_proposals",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="optimization_proposals",
        null=True,
        blank=True,
    )
    target_type = models.CharField(max_length=40, choices=OptimizationPolicy.TargetType.choices, db_index=True)
    target_reference = models.CharField(max_length=120, db_index=True)
    proposal_type = models.CharField(max_length=40, choices=OptimizationPolicy.ProposalType.choices, db_index=True)
    current_value = models.JSONField(default=dict, blank=True)
    proposed_value = models.JSONField(default=dict, blank=True)
    rationale = models.TextField()
    evidence_summary = models.TextField(blank=True)
    expected_impact_summary = models.TextField(blank=True)
    risk_level = models.CharField(max_length=20, choices=OptimizationPolicy.RiskLevel.choices, default=OptimizationPolicy.RiskLevel.MEDIUM, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW, db_index=True)
    policy_applied = models.ForeignKey(
        "ai_optimization_loop.OptimizationPolicy",
        on_delete=models.SET_NULL,
        related_name="proposals",
        null=True,
        blank=True,
    )
    source_outcome_type = models.CharField(max_length=40, blank=True, db_index=True)
    source_outcome_reference = models.CharField(max_length=120, blank=True, db_index=True)
    approved_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="optimization_proposals_approved",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_by_mode = models.CharField(max_length=20, choices=AppliedByMode.choices, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_optimization_proposals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="ai_opt_prop_comp_status_idx"),
            models.Index(fields=["target_type", "proposal_type"], name="ai_opt_prop_target_prop_idx"),
        ]


class OptimizationAuditTrail(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    proposal = models.ForeignKey(
        "ai_optimization_loop.OptimizationProposal",
        on_delete=models.CASCADE,
        related_name="audit_entries",
        null=True,
        blank=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="optimization_audit_entries",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=80, db_index=True)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_optimization_audit_trail"
        ordering = ["created_at", "id"]
