import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class SearchIndexEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_module = models.CharField(max_length=80, db_index=True)
    item_type = models.CharField(max_length=80, db_index=True)
    item_id = models.CharField(max_length=120, db_index=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    search_text = models.TextField()
    status = models.CharField(max_length=80, blank=True, db_index=True)
    category = models.CharField(max_length=80, blank=True, db_index=True)
    url_path = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "global_search_index_entries"
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["source_module", "item_type", "item_id"], name="uniq_search_index_entry"),
        ]

    def __str__(self) -> str:
        return self.title


class SearchQueryLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    query_text = models.CharField(max_length=255, db_index=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="search_query_logs",
        null=True,
        blank=True,
    )
    source_context = models.CharField(max_length=80, blank=True)
    filters_json = models.JSONField(default=dict, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    executed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "global_search_query_logs"
        ordering = ["-executed_at", "-created_at"]

    def __str__(self) -> str:
        return self.query_text


class SearchSavedFilter(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="saved_search_filters",
        null=True,
        blank=True,
    )
    owner_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="saved_search_filters",
        null=True,
        blank=True,
    )
    filter_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "global_search_saved_filters"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class SearchSynonym(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    term = models.CharField(max_length=120, db_index=True)
    synonym = models.CharField(max_length=120, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "global_search_synonyms"
        ordering = ["term", "synonym"]
        constraints = [
            models.UniqueConstraint(fields=["term", "synonym"], name="uniq_search_synonym_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.term} -> {self.synonym}"


class SearchBoostRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_module = models.CharField(max_length=80, blank=True)
    item_type = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=80, blank=True)
    boost_value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "global_search_boost_rules"
        ordering = ["-boost_value", "-created_at"]

    def __str__(self) -> str:
        return f"{self.source_module or '*'}:{self.item_type or '*'}:{self.status or '*'}"

