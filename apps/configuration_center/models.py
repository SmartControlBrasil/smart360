import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class SystemSetting(models.Model):
    class ValueType(models.TextChoices):
        STRING = "string", "String"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        JSON = "json", "JSON"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    key = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    group_name = models.CharField(max_length=120, db_index=True)
    module_name = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=20, choices=ValueType.choices, default=ValueType.STRING)
    value_string = models.TextField(blank=True)
    value_number = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)
    value_json = models.JSONField(default=dict, blank=True)
    default_value_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_sensitive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_system_settings"
        ordering = ["group_name", "key"]
        indexes = [
            models.Index(fields=["module_name", "is_active"], name="cfg_setting_module_active_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.key.replace(".", "-"))
        super().save(*args, **kwargs)

    @property
    def resolved_value(self):
        if self.value_type == self.ValueType.STRING:
            return self.value_string
        if self.value_type == self.ValueType.NUMBER:
            return self.value_number
        if self.value_type == self.ValueType.BOOLEAN:
            return self.value_boolean
        return self.value_json

    def __str__(self) -> str:
        return self.key


class FeatureFlag(models.Model):
    class FlagType(models.TextChoices):
        BOOLEAN = "boolean", "Boolean"
        ROLLOUT = "rollout", "Rollout"
        CONDITIONAL = "conditional", "Conditional"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    key = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    module_name = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True)
    flag_type = models.CharField(max_length=20, choices=FlagType.choices, default=FlagType.BOOLEAN)
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.PositiveIntegerField(default=0)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_feature_flags"
        ordering = ["key"]
        indexes = [
            models.Index(fields=["module_name", "is_active"], name="cfg_flag_module_active_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.key.replace(".", "-"))
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.key


class FeatureFlagScope(models.Model):
    class ScopeType(models.TextChoices):
        USER = "user", "User"
        COMPANY = "company", "Company"
        MODULE = "module", "Module"
        KEY = "key", "Key"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    feature_flag = models.ForeignKey(
        "configuration_center.FeatureFlag",
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices, default=ScopeType.COMPANY)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feature_flag_scopes",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="feature_flag_scopes",
        null=True,
        blank=True,
    )
    module_name = models.CharField(max_length=80, blank=True)
    scope_key = models.CharField(max_length=120, blank=True)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_feature_flag_scopes"
        ordering = ["feature_flag__key", "scope_type", "-created_at"]

    def __str__(self) -> str:
        return f"{self.feature_flag.key}:{self.scope_type}"


class ConfigurationAuditLog(models.Model):
    class ActionType(models.TextChoices):
        SETTING_CREATED = "setting_created", "Setting Created"
        SETTING_UPDATED = "setting_updated", "Setting Updated"
        FLAG_CREATED = "flag_created", "Flag Created"
        FLAG_UPDATED = "flag_updated", "Flag Updated"
        FLAG_ENABLED = "flag_enabled", "Flag Enabled"
        FLAG_DISABLED = "flag_disabled", "Flag Disabled"
        ROLLOUT_CHANGED = "rollout_changed", "Rollout Changed"
        PROFILE_UPDATED = "profile_updated", "Profile Updated"
        OVERRIDE_UPDATED = "override_updated", "Override Updated"
        TOGGLE_UPDATED = "toggle_updated", "Toggle Updated"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="configuration_audit_logs",
        null=True,
        blank=True,
    )
    setting_key = models.CharField(max_length=160, blank=True, db_index=True)
    feature_flag_key = models.CharField(max_length=160, blank=True, db_index=True)
    action_type = models.CharField(max_length=40, choices=ActionType.choices)
    old_value_json = models.JSONField(default=dict, blank=True)
    new_value_json = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "configuration_audit_logs"
        ordering = ["-changed_at", "-created_at"]

    def __str__(self) -> str:
        return self.action_type


class ModuleConfigurationProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    module_name = models.CharField(max_length=80, db_index=True)
    description = models.TextField(blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_module_profiles"
        ordering = ["module_name", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CompanyConfigurationOverride(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="configuration_overrides",
    )
    setting_key = models.CharField(max_length=160, db_index=True)
    override_value_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_company_overrides"
        ordering = ["company__name", "setting_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "setting_key"],
                name="uniq_company_setting_override",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company} - {self.setting_key}"


class RuntimeToggle(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    key = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    module_name = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuration_runtime_toggles"
        ordering = ["module_name", "key"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.key.replace(".", "-"))
        super().save(*args, **kwargs)

    @property
    def is_currently_enabled(self) -> bool:
        if not self.is_enabled:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    def __str__(self) -> str:
        return self.key
