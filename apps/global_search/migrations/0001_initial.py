import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchBoostRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(blank=True, max_length=80)),
                ("item_type", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(blank=True, max_length=80)),
                ("boost_value", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "global_search_boost_rules", "ordering": ["-boost_value", "-created_at"]},
        ),
        migrations.CreateModel(
            name="SearchIndexEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("item_type", models.CharField(db_index=True, max_length=80)),
                ("item_id", models.CharField(db_index=True, max_length=120)),
                ("title", models.CharField(max_length=255)),
                ("subtitle", models.CharField(blank=True, max_length=255)),
                ("body_text", models.TextField(blank=True)),
                ("search_text", models.TextField()),
                ("status", models.CharField(blank=True, db_index=True, max_length=80)),
                ("category", models.CharField(blank=True, db_index=True, max_length=80)),
                ("url_path", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "global_search_index_entries", "ordering": ["-updated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="SearchQueryLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("query_text", models.CharField(db_index=True, max_length=255)),
                ("source_context", models.CharField(blank=True, max_length=80)),
                ("filters_json", models.JSONField(blank=True, default=dict)),
                ("results_count", models.PositiveIntegerField(default=0)),
                ("executed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "performed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="search_query_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "global_search_query_logs", "ordering": ["-executed_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="SearchSavedFilter",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("filter_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saved_search_filters",
                        to="companies.company",
                    ),
                ),
                (
                    "owner_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saved_search_filters",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "global_search_saved_filters", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SearchSynonym",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("term", models.CharField(db_index=True, max_length=120)),
                ("synonym", models.CharField(db_index=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "global_search_synonyms", "ordering": ["term", "synonym"]},
        ),
        migrations.AddConstraint(
            model_name="searchindexentry",
            constraint=models.UniqueConstraint(fields=("source_module", "item_type", "item_id"), name="uniq_search_index_entry"),
        ),
        migrations.AddConstraint(
            model_name="searchsynonym",
            constraint=models.UniqueConstraint(fields=("term", "synonym"), name="uniq_search_synonym_pair"),
        ),
    ]

