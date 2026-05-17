import factory
from django.utils import timezone

from apps.companies.models import Company, Membership, SiteMembership
from apps.roles.models import Role
from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@smart360.local")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone_number = factory.Sequence(lambda n: f"+551199990{n:04d}")
    user_type = User.UserType.INTERNAL
    is_active = True
    is_staff = False
    is_verified = True
    date_joined = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "StrongPass123!"
        self.set_password(raw_password)
        if create:
            self.save(update_fields=["password", "updated_at"])


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Company {n}")
    legal_name = factory.LazyAttribute(lambda obj: f"{obj.name} LTDA")
    slug = factory.Sequence(lambda n: f"company-{n}")
    status = Company.Status.ACTIVE
    email = factory.LazyAttribute(lambda obj: f"contato@{obj.slug}.local")
    phone_number = factory.Sequence(lambda n: f"+55114000{n:04d}")
    metadata = factory.LazyFunction(dict)


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role

    code = factory.Sequence(lambda n: f"role_{n}")
    label = factory.Sequence(lambda n: f"Role {n}")
    scope = Role.Scope.COMPANY
    description = factory.Faker("sentence")
    is_system = True
    is_active = True
    metadata = factory.LazyFunction(dict)


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    status = Membership.Status.ACTIVE
    is_primary = True
    invited_at = factory.LazyFunction(timezone.now)
    joined_at = factory.LazyFunction(timezone.now)
    metadata = factory.LazyFunction(dict)

    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for role in extracted:
                self.roles.add(role)


class SiteMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteMembership

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    site = factory.SubFactory(
        "tests.factories.smart_system.OperationalSiteFactory",
        maintenance_client__company=factory.SelfAttribute("..company"),
    )
    status = SiteMembership.Status.ACTIVE
    is_primary = False
    metadata = factory.LazyFunction(dict)
