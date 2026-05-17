from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.ai_agents_center.models import AgentActionProposal
from apps.ai_shared.interfaces.autonomous_ops import get_autonomous_operations_service
from apps.ai_shared.interfaces.decision_engine import get_decision_execution_service
from apps.ai_decision_engine.models import AgentDecision, DecisionExecution
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.ai_simulation_engine.models import SimulationType
from apps.ai_simulation_engine.services.orchestrator import SimulationOrchestrator
from apps.ai_simulation_engine.services.policies import SimulationPolicyService
from apps.observability_center.services.observability_service import SystemEventService

from .approvals import DecisionApprovalService
from .audit import DecisionAuditService
from .classifier import ActionProposalClassifier
from .policies import DecisionPolicyEngine


class DecisionOrchestrator:
    @classmethod
    @transaction.atomic
    def receive_action_proposal(cls, *, proposal: AgentActionProposal):
        classification = ActionProposalClassifier.classify(proposal)
        company = proposal.agent_run.company
        site = proposal.agent_run.site
        decision, _ = AgentDecision.objects.update_or_create(
            agent_action_proposal=proposal,
            defaults={
                "company": company,
                "site": site,
                "action_type": proposal.action_type,
                "normalized_action_type": classification.normalized_action_type,
                "target_entity": proposal.target_entity,
                "target_entity_id": proposal.target_entity_id,
                "risk_level": classification.risk_level,
                "autonomy_level": classification.autonomy_level,
                "tenant_scope_mode": classification.tenant_scope_mode,
                "requires_human_approval": classification.requires_human_approval,
                "can_auto_execute": classification.can_auto_execute,
                "rollback_required": classification.rollback_required,
                "decision_status": AgentDecision.DecisionStatus.PENDING_POLICY,
                "decision_reason": "",
                "explainability_payload": {"classification": classification.signals},
                "execution_payload": proposal.proposed_payload or {},
            },
        )
        DecisionAuditService.log_event(
            decision=decision,
            event_type="decision.received",
            actor_mode="agent",
            actor_label=proposal.agent_run.agent.slug,
            message="Proposal recebida pelo AI Decision Engine.",
            metadata={"proposal_public_id": str(proposal.public_id), "action_type": proposal.action_type},
        )
        SystemEventService.log_system_event(
            event_type="decision.received",
            source_module="ai_decision_engine",
            message="Action proposal received by decision engine.",
            entity_type=proposal.target_entity or proposal.action_type,
            entity_id=proposal.target_entity_id or str(proposal.public_id),
            user=proposal.agent_run.triggered_by,
            company=company,
            site=site,
            payload={
                "proposal_public_id": str(proposal.public_id),
                "agent": proposal.agent_run.agent.slug,
                "action_type": proposal.action_type,
            },
        )
        evaluation = DecisionPolicyEngine.evaluate(
            proposal=proposal,
            classification=classification,
            company=company,
            site=site,
        )
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_decision_engine",
            action_type=classification.normalized_action_type,
            company=company,
            site=site,
            risk_level=classification.risk_level,
            autonomy_level=classification.autonomy_level,
            agent_slug=proposal.agent_run.agent.slug,
            context={"target_entity": proposal.target_entity, "proposal_action_type": proposal.action_type},
        )
        studio_payload = {
            "result": studio_result.result,
            "reason": studio_result.reason,
            "policy_public_id": str(studio_result.policy.public_id) if studio_result.policy else "",
            "rule_public_id": str(studio_result.rule.public_id) if studio_result.rule else "",
        }
        if studio_result.result == PolicyRule.EvaluationResult.DENY:
            evaluation = evaluation.__class__(
                policy=evaluation.policy,
                outcome=AgentDecision.DecisionStatus.AUTO_BLOCKED,
                reason=studio_result.reason,
                requires_human_approval=False,
                can_auto_execute=False,
                escalation_target="",
                approver_role_slugs=[],
                explainability_payload={**evaluation.explainability_payload, "policy_studio": studio_payload},
            )
        elif studio_result.result == PolicyRule.EvaluationResult.REQUIRE_APPROVAL:
            evaluation = evaluation.__class__(
                policy=evaluation.policy,
                outcome=AgentDecision.DecisionStatus.AWAITING_APPROVAL,
                reason=studio_result.reason,
                requires_human_approval=True,
                can_auto_execute=False,
                escalation_target="",
                approver_role_slugs=studio_result.approver_roles or evaluation.approver_role_slugs,
                explainability_payload={**evaluation.explainability_payload, "policy_studio": studio_payload},
            )
        elif studio_result.result == PolicyRule.EvaluationResult.ESCALATE:
            evaluation = evaluation.__class__(
                policy=evaluation.policy,
                outcome=AgentDecision.DecisionStatus.ESCALATED,
                reason=studio_result.reason,
                requires_human_approval=True,
                can_auto_execute=False,
                escalation_target="policy-studio-escalation",
                approver_role_slugs=studio_result.approver_roles or evaluation.approver_role_slugs,
                explainability_payload={**evaluation.explainability_payload, "policy_studio": studio_payload},
            )
        else:
            requires_human_approval = evaluation.requires_human_approval or studio_result.requires_approval
            outcome = evaluation.outcome
            if requires_human_approval and evaluation.outcome in {
                AgentDecision.DecisionStatus.APPROVED,
                AgentDecision.DecisionStatus.AUTO_APPROVED,
            }:
                outcome = AgentDecision.DecisionStatus.AWAITING_APPROVAL
            evaluation = evaluation.__class__(
                policy=evaluation.policy,
                outcome=outcome,
                reason=evaluation.reason,
                requires_human_approval=requires_human_approval,
                can_auto_execute=evaluation.can_auto_execute and not requires_human_approval,
                escalation_target=evaluation.escalation_target,
                approver_role_slugs=studio_result.approver_roles or evaluation.approver_role_slugs,
                explainability_payload={**evaluation.explainability_payload, "policy_studio": studio_payload},
            )
        simulation_requirement = SimulationPolicyService.get_requirement_for_decision(decision)
        experiment_assignment = ExperimentationEngine.resolve_assignment(
            target_component="decision_engine",
            target_reference=classification.normalized_action_type,
            entity_key=str(proposal.public_id),
            entity_type="decision",
            company=company,
            site=site,
            context={"agent_slug": proposal.agent_run.agent.slug, "risk_level": classification.risk_level},
        )
        decision.policy_applied = evaluation.policy
        decision.decision_status = evaluation.outcome
        decision.decision_reason = evaluation.reason
        decision.requires_human_approval = evaluation.requires_human_approval
        decision.can_auto_execute = evaluation.can_auto_execute
        decision.escalation_target = evaluation.escalation_target
        decision.explainability_payload = evaluation.explainability_payload
        if experiment_assignment is not None:
            decision.explainability_payload = {
                **(decision.explainability_payload or {}),
                "experiment": {
                    "experiment_public_id": str(experiment_assignment.experiment.public_id),
                    "assignment_public_id": str(experiment_assignment.public_id),
                    "variant_public_id": str(experiment_assignment.variant.public_id),
                    "variant_slug": experiment_assignment.variant.slug,
                    "variant_config": experiment_assignment.variant.config_payload,
                },
            }
        if simulation_requirement:
            decision.explainability_payload = {
                **(decision.explainability_payload or {}),
                "simulation_requirement": simulation_requirement,
            }
        decision.save(
            update_fields=[
                "policy_applied",
                "decision_status",
                "decision_reason",
                "requires_human_approval",
                "can_auto_execute",
                "escalation_target",
                "explainability_payload",
                "updated_at",
            ]
        )
        DecisionAuditService.log_event(
            decision=decision,
            event_type="decision.policy.applied",
            actor_mode="policy",
            actor_label=getattr(evaluation.policy, "slug", ""),
            message=evaluation.reason,
            metadata=evaluation.explainability_payload,
        )
        SystemEventService.log_system_event(
            event_type="decision.policy.applied",
            source_module="ai_decision_engine",
            message=evaluation.reason,
            entity_type=proposal.target_entity or classification.normalized_action_type,
            entity_id=proposal.target_entity_id or str(decision.public_id),
            company=company,
            site=site,
            payload={
                "decision_public_id": str(decision.public_id),
                "policy": getattr(evaluation.policy, "slug", ""),
                "outcome": evaluation.outcome,
                "risk_level": classification.risk_level,
            },
        )
        if experiment_assignment is not None:
            ExperimentationEngine.record_assignment_metric(
                assignment=experiment_assignment,
                metric_type="decision_received",
                value=1,
                unit="count",
                source_component="ai_decision_engine",
                source_reference=str(decision.public_id),
                metadata={"outcome": evaluation.outcome, "requires_human_approval": evaluation.requires_human_approval},
            )
        if simulation_requirement:
            simulation_run = SimulationOrchestrator.simulate_for_decision(
                decision=decision,
                requested_by=proposal.agent_run.triggered_by,
                force=False,
            )
            if simulation_run and simulation_run.result:
                decision.refresh_from_db()
        if evaluation.outcome in {AgentDecision.DecisionStatus.AWAITING_APPROVAL, AgentDecision.DecisionStatus.ESCALATED}:
            DecisionApprovalService.request_approval(
                decision=decision,
                requested_role_slugs=evaluation.approver_role_slugs,
                comment="Approval requested by policy engine.",
            )
            proposal.status = AgentActionProposal.Status.PENDING_APPROVAL
            proposal.save(update_fields=["status", "updated_at"])
            SystemEventService.log_system_event(
                event_type="decision.awaiting_approval",
                source_module="ai_decision_engine",
                message="Decision awaiting human approval.",
                entity_type=proposal.target_entity or classification.normalized_action_type,
                entity_id=proposal.target_entity_id or str(decision.public_id),
                company=company,
                site=site,
                payload={
                    "decision_public_id": str(decision.public_id),
                    "approval_roles": evaluation.approver_role_slugs,
                    "escalation_target": evaluation.escalation_target,
                    "simulation_required": bool(simulation_requirement and simulation_requirement["mode"] == SimulationType.PolicyMode.REQUIRED),
                },
            )
            return decision
        if evaluation.outcome == AgentDecision.DecisionStatus.AUTO_BLOCKED:
            proposal.status = AgentActionProposal.Status.REJECTED
            proposal.rejection_reason = evaluation.reason
            proposal.rejected_at = timezone.now()
            proposal.save(update_fields=["status", "rejection_reason", "rejected_at", "updated_at"])
            SystemEventService.log_system_event(
                event_type="decision.auto_blocked",
                source_module="ai_decision_engine",
                message=evaluation.reason,
                severity="warning",
                entity_type=proposal.target_entity or classification.normalized_action_type,
                entity_id=proposal.target_entity_id or str(decision.public_id),
                company=company,
                site=site,
                payload={"decision_public_id": str(decision.public_id)},
            )
            return decision
        if evaluation.can_auto_execute:
            proposal.status = AgentActionProposal.Status.EXECUTED
            proposal.approved_at = timezone.now()
            proposal.save(update_fields=["status", "approved_at", "updated_at"])
            autonomous_operations_service = get_autonomous_operations_service()
            autonomy_execution = autonomous_operations_service.evaluate_and_execute(decision=decision)
            if autonomy_execution.execution_status == "blocked":
                decision.refresh_from_db()
                decision.decision_status = AgentDecision.DecisionStatus.AWAITING_APPROVAL
                decision.decision_reason = autonomy_execution.execution_summary
                decision.save(update_fields=["decision_status", "decision_reason", "updated_at"])
                DecisionApprovalService.request_approval(
                    decision=decision,
                    requested_role_slugs=evaluation.approver_role_slugs or ["maintenance-manager"],
                    comment="Autonomy blocked candidate; moved to human approval.",
                )
                proposal.status = AgentActionProposal.Status.PENDING_APPROVAL
                proposal.save(update_fields=["status", "updated_at"])
                return decision
            decision.refresh_from_db()
            SystemEventService.log_system_event(
                event_type="decision.auto_approved",
                source_module="ai_decision_engine",
                message="Decision auto-approved and executed.",
                entity_type=proposal.target_entity or classification.normalized_action_type,
                entity_id=proposal.target_entity_id or str(decision.public_id),
                company=company,
                site=site,
                payload={"decision_public_id": str(decision.public_id)},
            )
            return decision
        proposal.status = AgentActionProposal.Status.APPROVED
        proposal.approved_at = timezone.now()
        proposal.save(update_fields=["status", "approved_at", "updated_at"])
        return decision

    @classmethod
    def approve_decision(cls, *, decision: AgentDecision, approved_by, comment: str = ""):
        execution = DecisionApprovalService.approve(
            decision=decision,
            approved_by=approved_by,
            comment=comment,
            execute=True,
        )
        proposal = decision.agent_action_proposal
        proposal.status = AgentActionProposal.Status.APPROVED
        proposal.approved_by = approved_by
        proposal.approved_at = timezone.now()
        proposal.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="decision.approved",
            source_module="ai_decision_engine",
            message="Decision approved.",
            entity_type=decision.target_entity or decision.normalized_action_type,
            entity_id=decision.target_entity_id or str(decision.public_id),
            user=approved_by,
            company=decision.company,
            site=decision.site,
            payload={"decision_public_id": str(decision.public_id)},
        )
        return execution

    @classmethod
    def reject_decision(cls, *, decision: AgentDecision, rejected_by, comment: str = ""):
        approval = DecisionApprovalService.reject(decision=decision, rejected_by=rejected_by, comment=comment)
        proposal = decision.agent_action_proposal
        proposal.status = AgentActionProposal.Status.REJECTED
        proposal.rejected_by = rejected_by
        proposal.rejected_at = timezone.now()
        proposal.rejection_reason = comment
        proposal.save(update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"])
        SystemEventService.log_system_event(
            event_type="decision.rejected",
            source_module="ai_decision_engine",
            message="Decision rejected.",
            entity_type=decision.target_entity or decision.normalized_action_type,
            entity_id=decision.target_entity_id or str(decision.public_id),
            user=rejected_by,
            company=decision.company,
            site=decision.site,
            payload={"decision_public_id": str(decision.public_id), "comment": comment},
        )
        return approval

    @classmethod
    def reexecute_decision(cls, *, decision: AgentDecision, requested_by):
        decision_execution_service = get_decision_execution_service()
        return decision_execution_service.execute(
            decision=decision,
            executed_by_mode=DecisionExecution.ExecutedByMode.REPLAY,
            executed_by_user=requested_by,
        )
