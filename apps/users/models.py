import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        INTERNAL = "internal", "Interno"
        CLIENT = "client", "Cliente"
        PARTNER = "partner", "Parceiro"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.INTERNAL,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["email"]

    def __str__(self) -> str:
        return self.full_name or self.email

    @property
    def full_name(self) -> str:
        return " ".join(part for part in [self.first_name, self.last_name] if part).strip()

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        if not self.display_name:
            self.display_name = self.full_name or self.email
        super().save(*args, **kwargs)
