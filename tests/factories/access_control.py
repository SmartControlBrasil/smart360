import factory
from django.utils import timezone

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission, UserRoleAssignment
from tests.factories.core import CompanyFactory, UserFactory


class PermissionDomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PermissionDomain

    name = factory.Sequence(lambda n: f"Domain {n}")
    description = factory.Faker("sentence")
    module_name = "billing"
    is_active = True


class PermissionActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PermissionAction

    domain = factory.SubFactory(PermissionDomainFactory)
    action_name = factory.Sequence(lambda n: f"action_{n}")
    description = factory.Faker("sentence")
    is_active = True


class AccessRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = __import__("apps.access_control_center.models", fromlist=["Role"]).Role

    name = factory.Sequence(lambda n: f"Access Role {n}")
    role_type = __import__("apps.access_control_center.models", fromlist=["Role"]).Role.RoleType.INTERNAL
    description = factory.Faker("sentence")
    is_system_role = False
    is_active = True


class RolePermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RolePermission

    role = factory.SubFactory(AccessRoleFactory)
    permission_domain = factory.SubFactory(PermissionDomainFactory)
    permission_action = factory.SubFactory(PermissionActionFactory, domain=factory.SelfAttribute("..permission_domain"))
    is_allowed = True


class UserRoleAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRoleAssignment

    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(AccessRoleFactory)
    company = factory.SubFactory(CompanyFactory)
    scope_type = UserRoleAssignment.ScopeType.COMPANY
    assigned_by = factory.SubFactory(UserFactory)
    assigned_at = factory.LazyFunction(timezone.now)
    is_active = True
