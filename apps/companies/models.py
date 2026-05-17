import uuid

from django.conf import settings
from django.db import models


class Company(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        INACTIVE = "inactive", "Inativa"
        SUSPENDED = "suspended", "Suspensa"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    tax_id = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INVITED = "invited", "Convidado"
        INACTIVE = "inactive", "Inativo"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    roles = models.ManyToManyField("roles.Role", related_name="memberships", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_memberships"
        ordering = ["company__name", "user__email"]
        constraints = [
            models.UniqueConstraint(fields=["user", "company"], name="uniq_user_company_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.company}"


class SiteMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="site_memberships",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="site_memberships",
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.CASCADE,
        related_name="site_memberships",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_site_memberships"
        ordering = ["company__name", "site__name", "user__email"]
        constraints = [
            models.UniqueConstraint(fields=["user", "site"], name="uniq_user_site_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.site}"
