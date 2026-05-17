from django.db.models import Q
from django.utils import timezone

from apps.access_control_center.models import (
    AccessAuditLog,
    AccessPolicy,
    PermissionAction,
    PermissionDomain,
    PolicyAssignment,
    RolePermission,
    SensitiveActionApproval,
    UserRoleAssignment,
)
from shared_kernel.observability.context import get_correlation_id, get_request_context, get_request_id


class AccessAuditService:
    @staticmethod
    def log(
        *,
        user,
        action,
        domain,
        decision,
        reason="",
        resource_type="",
        resource_id="",
        metadata=None,
        company=None,
        site=None,
        request_id="",
        correlation_id="",
        origin="",
        before_state=None,
        after_state=None,
    ):
        request_context = get_request_context()
        audit_log = AccessAuditLog.objects.create(
            user=user,
            company=company or request_context.get("company"),
            site=site or request_context.get("site"),
            action=action,
            domain=domain,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            decision=decision,
            request_id=request_id or get_request_id(),
            correlation_id=correlation_id or get_correlation_id(),
            origin=origin or request_context.get("origin", "web"),
            reason=reason,
            before_state=before_state or {},
            after_state=after_state or {},
            metadata=metadata or {},
        )
        try:
            from apps.observability_center.services.observability_service import SystemEventService

            SystemEventService.log_system_event(
                event_type=f"audit.{domain}.{action}",
                source_module=domain,
                message=f"Audit log recorded for {domain}.{action}.",
                severity="info" if decision == AccessAuditLog.Decision.ALLOW else "warning",
                entity_type=resource_type,
                entity_id=str(resource_id or ""),
                user=user,
                company=audit_log.company,
                site=audit_log.site,
                request_id=audit_log.request_id,
                correlation_id=audit_log.correlation_id,
                request_path=request_context.get("path", ""),
                request_method=request_context.get("method", ""),
                payload={
                    "decision": decision,
                    "origin": audit_log.origin,
                    "metadata": metadata or {},
                },
            )
        except Exception:
            pass
        return audit_log


class RoleAssignmentService:
    @staticmethod
    def get_current_assignments(user, company=None, module_name="", resource_reference=""):
        now = timezone.now()
        queryset = UserRoleAssignment.objects.select_related("role", "company").filter(user=user, is_active=True)
        queryset = queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        if company:
            company_id = getattr(company, "id", company)
            queryset = queryset.filter(
                Q(scope_type=UserRoleAssignment.ScopeType.GLOBAL)
                | Q(scope_type=UserRoleAssignment.ScopeType.COMPANY, company_id=company_id)
                | Q(scope_type=UserRoleAssignment.ScopeType.MODULE, scope_reference=module_name)
                | Q(scope_type=UserRoleAssignment.ScopeType.RESOURCE, scope_reference=resource_reference)
            )
        elif module_name or resource_reference:
            queryset = queryset.filter(
                Q(scope_type=UserRoleAssignment.ScopeType.GLOBAL)
                | Q(scope_type=UserRoleAssignment.ScopeType.MODULE, scope_reference=module_name)
                | Q(scope_type=UserRoleAssignment.ScopeType.RESOURCE, scope_reference=resource_reference)
            )
        return queryset


class PolicyEvaluationService:
    @staticmethod
    def _compare(value, operator, expected, *, user=None, company=None):
        if operator == "eq":
            return value == expected
        if operator == "ne":
            return value != expected
        if operator == "in":
            return value in (expected or [])
        if operator == "contains":
            return expected in (value or [])
        if operator == "truthy":
            return bool(value)
        if operator == "falsy":
            return not bool(value)
        if operator == "equals_user_id":
            return str(value) == str(getattr(user, "id", ""))
        if operator == "equals_company_id":
            return str(value) == str(getattr(company, "id", company or ""))
        return False

    @classmethod
    def evaluate_policy(cls, policy, *, user=None, company=None, context=None):
        context = context or {}
        definition = policy.rule_definition_json or {}
        conditions = definition.get("conditions", [])
        logic = definition.get("logic", "all")
        if not conditions:
            return True, "No conditions configured."

        results = []
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "eq")
            expected = condition.get("value")
            actual = context.get(field)
            results.append(cls._compare(actual, operator, expected, user=user, company=company))

        allowed = all(results) if logic == "all" else any(results)
        return allowed, f"Policy {policy.slug} evaluated with logic={logic}."

    @classmethod
    def evaluate_effective_policies(cls, *, user, domain, company=None, context=None, roles=None):
        assignments = PolicyAssignment.objects.select_related("policy", "role", "company", "user").filter(
            policy__domain=domain,
            policy__is_active=True,
            is_active=True,
        )
        if roles:
            assignments = assignments.filter(Q(role__in=roles) | Q(user=user) | Q(company=company) | Q(role__isnull=True))
        else:
            assignments = assignments.filter(Q(user=user) | Q(company=company) | Q(role__isnull=True))

        matched = []
        reasons = []
        for assignment in assignments.distinct():
            policy = assignment.policy
            allowed, reason = cls.evaluate_policy(policy, user=user, company=company, context=context or {})
            matched.append(allowed)
            reasons.append(reason)
        return (all(matched) if matched else True), reasons


class AccessControlService:
    @staticmethod
    def get_user_permissions(user, *, company=None, module_name=""):
        assignments = RoleAssignmentService.get_current_assignments(user, company=company, module_name=module_name)
        roles = [assignment.role for assignment in assignments]
        permissions = RolePermission.objects.select_related(
            "role",
            "permission_domain",
            "permission_action",
        ).filter(role__in=roles, permission_domain__is_active=True, permission_action__is_active=True)

        aggregated = {}
        for permission in permissions:
            key = (permission.permission_domain.slug, permission.permission_action.slug)
            item = aggregated.setdefault(
                key,
                {
                    "domain": permission.permission_domain.slug,
                    "domain_name": permission.permission_domain.name,
                    "module_name": permission.permission_domain.module_name,
                    "action": permission.permission_action.action_name,
                    "action_slug": permission.permission_action.slug,
                    "roles": [],
                    "is_allowed": False,
                    "has_explicit_deny": False,
                },
            )
            item["roles"].append(permission.role.slug)
            if permission.is_allowed:
                item["is_allowed"] = True
            else:
                item["has_explicit_deny"] = True

        results = []
        for item in aggregated.values():
            item["roles"] = sorted(set(item["roles"]))
            item["effective_decision"] = "deny" if item["has_explicit_deny"] else ("allow" if item["is_allowed"] else "deny")
            results.append(item)
        return sorted(results, key=lambda entry: (entry["module_name"], entry["domain"], entry["action"]))

    @classmethod
    def check_permission(
        cls,
        *,
        user,
        domain_slug,
        action_slug,
        company=None,
        module_name="",
        resource_type="",
        resource_id="",
        context=None,
        log_decision=True,
    ):
        if getattr(user, "is_superuser", False):
            if log_decision:
                AccessAuditService.log(
                    user=user,
                    action=action_slug,
                    domain=domain_slug,
                    decision=AccessAuditLog.Decision.ALLOW,
                    reason="Superuser bypass.",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    metadata={"module_name": module_name},
                )
            return True, "Superuser bypass."

        resource_reference = f"{resource_type}:{resource_id}" if resource_type and resource_id else ""
        assignments = RoleAssignmentService.get_current_assignments(
            user,
            company=company,
            module_name=module_name,
            resource_reference=resource_reference,
        )
        roles = [assignment.role for assignment in assignments]
        domain = PermissionDomain.objects.filter(Q(slug=domain_slug) | Q(name__iexact=domain_slug), is_active=True).first()
        action = PermissionAction.objects.filter(
            Q(slug=action_slug) | Q(action_name__iexact=action_slug),
            is_active=True,
        ).first()
        if not domain or not action:
            reason = "Permission domain or action not found."
            if log_decision:
                AccessAuditService.log(
                    user=user,
                    action=action_slug,
                    domain=domain_slug,
                    decision=AccessAuditLog.Decision.DENY,
                    reason=reason,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
            return False, reason

        permissions = RolePermission.objects.filter(
            role__in=roles,
            permission_domain=domain,
            permission_action=action,
        )
        if permissions.filter(is_allowed=False).exists():
            reason = "Explicit deny from role permission."
            if log_decision:
                AccessAuditService.log(
                    user=user,
                    action=action_slug,
                    domain=domain_slug,
                    decision=AccessAuditLog.Decision.DENY,
                    reason=reason,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    metadata={"roles": [role.slug for role in roles]},
                )
            return False, reason

        allowed_by_rbac = permissions.filter(is_allowed=True).exists()
        if not allowed_by_rbac:
            reason = "No matching allow permission."
            if log_decision:
                AccessAuditService.log(
                    user=user,
                    action=action_slug,
                    domain=domain_slug,
                    decision=AccessAuditLog.Decision.DENY,
                    reason=reason,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    metadata={"roles": [role.slug for role in roles]},
                )
            return False, reason

        policies_ok, policy_reasons = PolicyEvaluationService.evaluate_effective_policies(
            user=user,
            domain=domain,
            company=company,
            context=context or {},
            roles=roles,
        )
        decision = AccessAuditLog.Decision.ALLOW if policies_ok else AccessAuditLog.Decision.DENY
        reason = "RBAC allow." if policies_ok else "Policy denied access."
        if policy_reasons:
            reason = f"{reason} {' '.join(policy_reasons)}"
        if log_decision:
            AccessAuditService.log(
                user=user,
                action=action_slug,
                domain=domain_slug,
                decision=decision,
                reason=reason,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata={"roles": [role.slug for role in roles], "context": context or {}},
            )
        return policies_ok, reason


class SensitiveActionApprovalService:
    @staticmethod
    def approve(*, approval, approved_by):
        approval.status = SensitiveActionApproval.Status.APPROVED
        approval.approved_by = approved_by
        approval.approved_at = timezone.now()
        approval.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return approval

    @staticmethod
    def reject(*, approval, approved_by):
        approval.status = SensitiveActionApproval.Status.REJECTED
        approval.approved_by = approved_by
        approval.approved_at = timezone.now()
        approval.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return approval
