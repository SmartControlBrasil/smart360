from django.db.models import Q
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine

from .appliers import OptimizationApplierService
from .audit import OptimizationAuditService


class OptimizationApprovalService:
    @classmethod
    def user_can_approve(cls, *, proposal, user):
        if getattr(user, "is_superuser", False):
            return True, "Superuser bypass."
        allowed, reason = AccessControlService.check_permission(
            user=user,
            domain_slug="ai_agents_admin",
            action_slug="approve",
            company=proposal.company,
            module_name="ai_optimization_loop",
            resource_type=proposal.target_type,
            resource_id=proposal.target_reference,
            log_decision=False,
        )
        if not allowed:
            return False, reason
        policy = proposal.policy_applied
        if policy and policy.approver_role_slugs:
            assignments = UserRoleAssignment.objects.select_related("role").filter(
                user=user,
                is_active=True,
                role__slug__in=policy.approver_role_slugs,
            ).filter(Q(company=proposal.company) | Q(company__isnull=True))
            if not any(assignment.is_current for assignment in assignments):
                return False, "Usuario nao possui role autorizada para aprovar este ajuste."
        return True, "Approval permitted."

    @classmethod
    def approve(cls, *, proposal: OptimizationProposal, approved_by, comment="", apply=True):
        allowed, reason = cls.user_can_approve(proposal=proposal, user=approved_by)
        if not allowed:
            raise PermissionError(reason)
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_optimization_loop",
            action_type=proposal.proposal_type,
            company=proposal.company,
            site=proposal.site,
            risk_level=proposal.risk_level,
            autonomy_level=0,
            context={"target_type": proposal.target_type},
        )
        if not studio_result.allowed or studio_result.result == PolicyRule.EvaluationResult.DENY:
            raise PermissionError(studio_result.reason)
        proposal.status = OptimizationProposal.Status.APPROVED
        proposal.approved_by_user = approved_by
        proposal.approved_at = timezone.now()
        proposal.rejection_reason = ""
        proposal.metadata = {**(proposal.metadata or {}), "approval_comment": comment}
        proposal.save(update_fields=["status", "approved_by_user", "approved_at", "rejection_reason", "metadata", "updated_at"])
        OptimizationAuditService.log_event(
            proposal=proposal,
            actor_user=approved_by,
            event_type="optimization.proposal.approved",
            message="Optimization proposal approved.",
            payload={"comment": comment},
        )
        if apply:
            return OptimizationApplierService.apply(proposal=proposal, applied_by_mode=OptimizationProposal.AppliedByMode.USER, actor_user=approved_by)
        return proposal

    @classmethod
    def reject(cls, *, proposal: OptimizationProposal, rejected_by, comment=""):
        allowed, reason = cls.user_can_approve(proposal=proposal, user=rejected_by)
        if not allowed:
            raise PermissionError(reason)
        proposal.status = OptimizationProposal.Status.REJECTED
        proposal.rejection_reason = comment
        proposal.approved_by_user = rejected_by
        proposal.approved_at = timezone.now()
        proposal.save(update_fields=["status", "rejection_reason", "approved_by_user", "approved_at", "updated_at"])
        OptimizationAuditService.log_event(
            proposal=proposal,
            actor_user=rejected_by,
            event_type="optimization.proposal.rejected",
            message="Optimization proposal rejected.",
            payload={"comment": comment},
        )
        return proposal
