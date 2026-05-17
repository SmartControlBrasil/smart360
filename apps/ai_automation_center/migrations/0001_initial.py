import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("files_center", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIContextProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("context_schema", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ai_context_profiles", "ordering": ["source_module", "name"]},
        ),
        migrations.CreateModel(
            name="AIModelConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("provider_name", models.CharField(max_length=80)),
                ("model_identifier", models.CharField(max_length=160)),
                (
                    "model_type",
                    models.CharField(
                        choices=[
                            ("chat", "Chat"),
                            ("completion", "Completion"),
                            ("embedding", "Embedding"),
                            ("classifier", "Classifier"),
                            ("reranker", "Reranker"),
                        ],
                        default="chat",
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ai_model_configs", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AITaskType",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "task_category",
                    models.CharField(
                        choices=[
                            ("summarization", "Summarization"),
                            ("classification", "Classification"),
                            ("extraction", "Extraction"),
                            ("recommendation", "Recommendation"),
                            ("generation", "Generation"),
                            ("diagnosis", "Diagnosis"),
                            ("search_enrichment", "Search Enrichment"),
                        ],
                        default="generation",
                        max_length=30,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ai_task_types", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="RetrievalSourceConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("source_type", models.CharField(max_length=80)),
                ("source_module", models.CharField(blank=True, db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ai_retrieval_source_configs", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PromptTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("source_module", models.CharField(blank=True, db_index=True, max_length=80)),
                ("prompt_role", models.CharField(blank=True, max_length=80)),
                ("prompt_template", models.TextField()),
                ("expected_output_schema", models.JSONField(blank=True, default=dict)),
                ("model_hint", models.CharField(blank=True, max_length=120)),
                ("version_label", models.CharField(default="v1", max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_prompt_templates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prompt_templates",
                        to="ai_automation_center.aitasktype",
                    ),
                ),
            ],
            options={"db_table": "ai_prompt_templates", "ordering": ["name", "-created_at"]},
        ),
        migrations.CreateModel(
            name="PromptVersion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("version_label", models.CharField(max_length=40)),
                ("prompt_template_snapshot", models.TextField()),
                ("expected_output_schema", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_prompt_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "prompt_template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="ai_automation_center.prompttemplate",
                    ),
                ),
            ],
            options={"db_table": "ai_prompt_versions", "ordering": ["prompt_template__name", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AITaskRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("source_reference_type", models.CharField(blank=True, max_length=80)),
                ("source_reference_id", models.CharField(blank=True, max_length=120)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("model_name", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "context_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="task_requests",
                        to="ai_automation_center.aicontextprofile",
                    ),
                ),
                (
                    "prompt_template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="task_requests",
                        to="ai_automation_center.prompttemplate",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_task_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_requests",
                        to="ai_automation_center.aitasktype",
                    ),
                ),
            ],
            options={"db_table": "ai_task_requests", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AITaskExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "execution_mode",
                    models.CharField(
                        choices=[
                            ("sync", "Sync"),
                            ("async", "Async"),
                            ("manual", "Manual"),
                            ("simulated", "Simulated"),
                        ],
                        default="simulated",
                        max_length=20,
                    ),
                ),
                ("provider_name", models.CharField(blank=True, max_length=80)),
                ("model_name", models.CharField(blank=True, max_length=120)),
                ("prompt_snapshot", models.TextField(blank=True)),
                ("input_snapshot", models.JSONField(blank=True, default=dict)),
                ("output_text", models.TextField(blank=True)),
                ("output_json", models.JSONField(blank=True, default=dict)),
                ("token_usage_input", models.PositiveIntegerField(blank=True, null=True)),
                ("token_usage_output", models.PositiveIntegerField(blank=True, null=True)),
                ("cost_estimate", models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="running",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "task_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="executions",
                        to="ai_automation_center.aitaskrequest",
                    ),
                ),
            ],
            options={"db_table": "ai_task_executions", "ordering": ["-started_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AutomationRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("trigger_event", models.CharField(db_index=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "prompt_template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="automation_rules",
                        to="ai_automation_center.prompttemplate",
                    ),
                ),
                (
                    "task_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_rules",
                        to="ai_automation_center.aitasktype",
                    ),
                ),
            ],
            options={"db_table": "ai_automation_rules", "ordering": ["source_module", "name"]},
        ),
        migrations.CreateModel(
            name="AIGeneratedArtifact",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("artifact_type", models.CharField(db_index=True, max_length=80)),
                ("title", models.CharField(blank=True, max_length=180)),
                ("content_text", models.TextField(blank=True)),
                ("content_json", models.JSONField(blank=True, default=dict)),
                ("is_approved", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_ai_generated_artifacts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "related_file",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_generated_artifacts",
                        to="files_center.storedfile",
                    ),
                ),
                (
                    "task_execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generated_artifacts",
                        to="ai_automation_center.aitaskexecution",
                    ),
                ),
            ],
            options={"db_table": "ai_generated_artifacts", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AutomationExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_reference_type", models.CharField(blank=True, max_length=80)),
                ("source_reference_id", models.CharField(blank=True, max_length=120)),
                ("integration_event_id", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("output_summary", models.TextField(blank=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "automation_rule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="executions",
                        to="ai_automation_center.automationrule",
                    ),
                ),
            ],
            options={"db_table": "ai_automation_executions", "ordering": ["-started_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AIAnnotation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("annotation_type", models.CharField(max_length=80)),
                ("feedback_label", models.CharField(blank=True, max_length=80)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "annotated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_annotations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "generated_artifact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="annotations",
                        to="ai_automation_center.aigeneratedartifact",
                    ),
                ),
            ],
            options={"db_table": "ai_annotations", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="promptversion",
            constraint=models.UniqueConstraint(
                fields=("prompt_template", "version_label"),
                name="uniq_ai_prompt_template_version",
            ),
        ),
    ]

