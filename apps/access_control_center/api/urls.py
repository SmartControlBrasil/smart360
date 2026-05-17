from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.access_control_center.api.views import (
    AccessAuditLogViewSet,
    AccessPolicyViewSet,
    CheckPermissionView,
    MyPermissionsView,
    MyRolesView,
    PermissionActionViewSet,
    PermissionDomainViewSet,
    PolicyAssignmentViewSet,
    PolicyEvaluationView,
    RolePermissionViewSet,
    RoleViewSet,
    SensitiveActionApprovalViewSet,
    UserRoleAssignmentViewSet,
)

router = DefaultRouter()
router.register("permission-domains", PermissionDomainViewSet, basename="access-control-permission-domain")
router.register("permission-actions", PermissionActionViewSet, basename="access-control-permission-action")
router.register("roles", RoleViewSet, basename="access-control-role")
router.register("role-permissions", RolePermissionViewSet, basename="access-control-role-permission")
router.register("user-role-assignments", UserRoleAssignmentViewSet, basename="access-control-user-role-assignment")
router.register("access-policies", AccessPolicyViewSet, basename="access-control-policy")
router.register("policy-assignments", PolicyAssignmentViewSet, basename="access-control-policy-assignment")
router.register("audit-logs", AccessAuditLogViewSet, basename="access-control-audit-log")
router.register("sensitive-approvals", SensitiveActionApprovalViewSet, basename="access-control-sensitive-approval")

urlpatterns = router.urls + [
    path("check-permission/", CheckPermissionView.as_view(), name="access-control-check-permission"),
    path("my-roles/", MyRolesView.as_view(), name="access-control-my-roles"),
    path("my-permissions/", MyPermissionsView.as_view(), name="access-control-my-permissions"),
    path("policy-evaluation/", PolicyEvaluationView.as_view(), name="access-control-policy-evaluation"),
]

