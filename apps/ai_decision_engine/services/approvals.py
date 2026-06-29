from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_shared.interfaces.decision_engine import get_decision_execution_service
from apps.ai_decision_engine.models import AgentDecision, DecisionApproval, DecisionExecution
from apps.ai_simulation_engine.models import SimulationType
from apps.ai_simulation_engine.services.decision_support import SimulationDecisionSupportService
from apps.observability_center.services.observability_service import SystemEventService

from .audit import ALLOW, DENY, DecisionAuditService


class DecisionApprovalService:
    @staticmethod
    def latest_pending(decision: AgentDecision):
        return decision.approvals.filter(approval_status=DecisionApproval.ApprovalStatus.PENDING).order_by("-created_at").first()

    @classmethod
    def user_can_approve(cls, *, decision: AgentDecision, user) -> tuple[bool, str]:
        if getattr(user, "is_superuser", False):
            return True, "Superuser bypass."
        company = decision.company
        allowed, reason = AccessControlService.check_permission(
            user=user,
            domain_slug="ai_agents_admin",
            action_slug="approve",
            company=company,
            module_name="ai_decision_engine",
            resource_type=decision.target_entity or decision.normalized_action_type,
            resource_id=decision.target_entity_id or str(decision.public_id),
            log_decision=False,
        )
        if not allowed:
            return False, reason
        policy = decision.policy_applied
        if policy and policy.approver_role_slugs:
            assignments = UserRoleAssignment.objects.select_related("role").filter(
                user=user,
                is_active=True,
                role__slug__in=policy.approver_role_slugs,
            ).filter(Q(company=company) | Q(company__isnull=True))
            current_assignments = [assignment for assignment in assignments if assignment.is_current]
            if not current_assignments:
                return False, "Usuario nao possui role autorizada para aprovar esta decisao."
        return True, "Approval permitted."

    @classmethod
    def request_approval(cls, *, decision: AgentDecision, requested_role_slugs: list[str], comment: str = ""):
        approval = cls.latest_pending(decision)
        if approval:
            return approval
        return DecisionApproval.objects.create(
            decision=decision,
            approval_status=DecisionApproval.ApprovalStatus.PENDING,
            requested_role_slugs=requested_role_slugs,
            comment=comment,
        )

    @classmethod
    def approve(cls, *, decision: AgentDecision, approved_by, comment: str = "", execute: bool = True):
        allowed, reason = cls.user_can_approve(decision=decision, user=approved_by)
        if not allowed:
            DecisionAuditService.log_access(
                decision=decision,
                user=approved_by,
                action="approve",
                decision_outcome=DENY,
                reason=reason,
                metadata={"decision_public_id": str(decision.public_id)},
            )
            raise PermissionError(reason)
        requirement = SimulationDecisionSupportService.get_requirement(decision=decision)
        satisfies_requirement, latest_run = SimulationDecisionSupportService.simulation_satisfies_requirement(decision=decision)
        if requirement and requirement["mode"] == SimulationType.PolicyMode.REQUIRED and not satisfies_requirement:
            reason = "Simulation obrigatoria ausente para esta decisao."
            DecisionAuditService.log_access(
                decision=decision,
                user=approved_by,
                action="approve",
                decision_outcome=DENY,
                reason=reason,
                metadata={"decision_public_id": str(decision.public_id), "required_simulation_type": requirement["simulation_type"]},
            )
            raise PermissionError(reason)
        approval = cls.request_approval(
            decision=decision,
            requested_role_slugs=list(decision.policy_applied.approver_role_slugs) if decision.policy_applied else [],
        )
        approval.approval_status = DecisionApproval.ApprovalStatus.APPROVED
        approval.approver_user = approved_by
        approval.comment = comment
        approval.approved_at = timezone.now()
        approval.save(update_fields=["approval_status", "approver_user", "comment", "approved_at", "updated_at"])
        decision.decision_status = AgentDecision.DecisionStatus.APPROVED
        decision.decision_reason = comment or "Approved by human approver."
        decision.decided_by_user = approved_by
        decision.decided_at = timezone.now()
        decision.save(update_fields=["decision_status", "decision_reason", "decided_by_user", "decided_at", "updated_at"])
        DecisionAuditService.log_access(
            decision=decision,
            user=approved_by,
            action="approve",
            decision_outcome=ALLOW,
            reason="Decision approved.",
            metadata={"decision_public_id": str(decision.public_id)},
        )
        DecisionAuditService.log_event(
            decision=decision,
            event_type="decision.approved",
            actor_mode="user",
            actor_user=approved_by,
            message="Decisao aprovada por humano.",
            metadata={
                "comment": comment,
                "simulation_run_public_id": str(latest_run.public_id) if latest_run else "",
            },
        )
        if execute:
            from .handlers import DecisionHandlerRegistry

            if DecisionHandlerRegistry.get_handler(decision.normalized_action_type) is None:
                decision.decision_reason = (
                    f"Approved without execution: no handler registered for {decision.normalized_action_type}."
                )
                decision.save(update_fields=["decision_reason", "updated_at"])
                DecisionAuditService.log_event(
                    decision=decision,
                    event_type="decision.execution.not_available",
                    actor_mode="system",
                    actor_user=approved_by,
                    message=decision.decision_reason,
                    metadata={"action_type": decision.action_type, "normalized_action_type": decision.normalized_action_type},
                )
                SystemEventService.log_system_event(
                    event_type="decision.execution.not_available",
                    source_module="ai_decision_engine",
                    message=decision.decision_reason,
                    severity="warning",
                    entity_type=decision.target_entity or decision.normalized_action_type,
                    entity_id=decision.target_entity_id or str(decision.public_id),
                    user=approved_by,
                    company=decision.company,
                    site=decision.site,
                    payload={
                        "decision_public_id": str(decision.public_id),
                        "action_type": decision.action_type,
                        "normalized_action_type": decision.normalized_action_type,
                    },
                )
                return approval
            decision_execution_service = get_decision_execution_service()
            return decision_execution_service.execute(
                decision=decision,
                executed_by_mode=DecisionExecution.ExecutedByMode.USER,
                executed_by_user=approved_by,
            )
        return approval

    @classmethod
    def reject(cls, *, decision: AgentDecision, rejected_by, comment: str = ""):
        allowed, reason = cls.user_can_approve(decision=decision, user=rejected_by)
        if not allowed:
            DecisionAuditService.log_access(
                decision=decision,
                user=rejected_by,
                action="reject",
                decision_outcome=DENY,
                reason=reason,
                metadata={"decision_public_id": str(decision.public_id)},
            )
            raise PermissionError(reason)
        approval = cls.request_approval(
            decision=decision,
            requested_role_slugs=list(decision.policy_applied.approver_role_slugs) if decision.policy_applied else [],
        )
        approval.approval_status = DecisionApproval.ApprovalStatus.REJECTED
        approval.approver_user = rejected_by
        approval.comment = comment
        approval.approved_at = timezone.now()
        approval.save(update_fields=["approval_status", "approver_user", "comment", "approved_at", "updated_at"])
        decision.decision_status = AgentDecision.DecisionStatus.REJECTED
        decision.decision_reason = comment or "Rejected by human approver."
        decision.decided_by_user = rejected_by
        decision.decided_at = timezone.now()
        decision.save(update_fields=["decision_status", "decision_reason", "decided_by_user", "decided_at", "updated_at"])
        DecisionAuditService.log_access(
            decision=decision,
            user=rejected_by,
            action="reject",
            decision_outcome=ALLOW,
            reason="Decision rejected.",
            metadata={"decision_public_id": str(decision.public_id)},
        )
        DecisionAuditService.log_event(
            decision=decision,
            event_type="decision.rejected",
            actor_mode="user",
            actor_user=rejected_by,
            message="Decisao rejeitada por humano.",
            metadata={"comment": comment},
        )
        return approval
