from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


def seed_experiment_policy(apps, schema_editor):
    Policy = apps.get_model("ai_policy_studio", "Policy")
    PolicyScope = apps.get_model("ai_policy_studio", "PolicyScope")
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")

    policy, _ = Policy.objects.get_or_create(
        slug="global-experiment-governance",
        defaults={
            "name": "Global Experiment Governance",
            "description": "Governanca central para criacao, atribuicao e promocao de experimentos de IA.",
            "tenant_scope": "global",
            "is_global": True,
            "status": "active",
            "version": 1,
        },
    )
    PolicyScope.objects.get_or_create(
        policy=policy,
        company=None,
        site=None,
        module_slug="ai_experimentation_framework",
        action_type="",
        agent_slug="",
        copilot_key="",
        defaults={"priority": 20},
    )
    rules = [
        {
            "action_type": "create_experiment",
            "risk_level": "medium",
            "result": "allow",
            "allowed": True,
            "requires_approval": False,
            "approver_roles": ["ai-governance-admin"],
            "rationale": "Criacao de experimento e permitida sob governanca central e escopo auditavel.",
        },
        {
            "action_type": "assign_variant",
            "risk_level": "low",
            "result": "allow",
            "allowed": True,
            "requires_approval": False,
            "approver_roles": [],
            "rationale": "Assignment controlado de variantes em runtime e permitido.",
        },
        {
            "action_type": "record_metric",
            "risk_level": "low",
            "result": "allow",
            "allowed": True,
            "requires_approval": False,
            "approver_roles": [],
            "rationale": "Coleta de metricas e permitida para auditoria e comparacao.",
        },
        {
            "action_type": "complete_experiment",
            "risk_level": "medium",
            "result": "allow",
            "allowed": True,
            "requires_approval": False,
            "approver_roles": ["ai-governance-admin"],
            "rationale": "Conclusao do experimento com analise persistida e permitida.",
        },
        {
            "action_type": "promote_variant",
            "risk_level": "high",
            "result": "require_approval",
            "allowed": True,
            "requires_approval": True,
            "approver_roles": ["ai-governance-admin", "maintenance-manager"],
            "rationale": "Promocao de variante em producao exige aprovacao humana.",
        },
    ]
    for item in rules:
        PolicyRule.objects.get_or_create(
            policy=policy,
            action_type=item["action_type"],
            risk_level=item["risk_level"],
            defaults={
                "autonomy_level": 1,
                "requires_approval": item["requires_approval"],
                "allowed": item["allowed"],
                "result": item["result"],
                "approver_roles": item["approver_roles"],
                "conditions": {},
                "rationale": item["rationale"],
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        ("ai_policy_studio", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Experiment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("target_component", models.CharField(choices=[("agent", "Agent"), ("copilot", "Copilot"), ("decision_engine", "Decision Engine"), ("simulation_engine", "Simulation Engine"), ("policy", "Policy"), ("heuristic", "Heuristic")], db_index=True, max_length=30)),
                ("target_reference", models.CharField(blank=True, db_index=True, max_length=180)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("running", "Running"), ("completed", "Completed"), ("promoted", "Promoted"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("start_date", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("end_date", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("traffic_split", models.JSONField(blank=True, default=dict)),
                ("assignment_strategy", models.CharField(choices=[("random", "Random"), ("weighted", "Weighted"), ("rule_based", "Rule Based")], db_index=True, default="weighted", max_length=20)),
                ("primary_metric", models.CharField(db_index=True, default="effectiveness_score", max_length=80)),
                ("success_direction", models.CharField(choices=[("higher_is_better", "Higher Is Better"), ("lower_is_better", "Lower Is Better")], default="higher_is_better", max_length=20)),
                ("min_sample_size", models.PositiveIntegerField(default=20)),
                ("min_runtime_hours", models.PositiveIntegerField(default=24)),
                ("auto_promote", models.BooleanField(default=False)),
                ("configuration_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_experiments", to="companies.company")),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_experiments_created", to=settings.AUTH_USER_MODEL)),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_experiments", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_experimentation_experiments", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Variant",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=140)),
                ("description", models.TextField(blank=True)),
                ("config_payload", models.JSONField(blank=True, default=dict)),
                ("weight", models.PositiveIntegerField(default=50)),
                ("enabled", models.BooleanField(default=True)),
                ("is_control", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("experiment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="ai_experimentation_framework.experiment")),
            ],
            options={"db_table": "ai_experimentation_variants", "ordering": ["experiment_id", "name"], "unique_together": {("experiment", "slug")}},
        ),
        migrations.AddField(
            model_name="experiment",
            name="winner_variant",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="winning_experiments", to="ai_experimentation_framework.variant"),
        ),
        migrations.CreateModel(
            name="ExperimentAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("entity_key", models.CharField(db_index=True, max_length=180)),
                ("entity_type", models.CharField(blank=True, db_index=True, max_length=80)),
                ("assignment_reason", models.CharField(blank=True, max_length=80)),
                ("context_payload", models.JSONField(blank=True, default=dict)),
                ("assigned_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_experiment_assignments", to="companies.company")),
                ("experiment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="ai_experimentation_framework.experiment")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_experiment_assignments", to="smart_system.operationalsite")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="ai_experimentation_framework.variant")),
            ],
            options={"db_table": "ai_experimentation_assignments", "ordering": ["-assigned_at"], "unique_together": {("experiment", "entity_key")}},
        ),
        migrations.CreateModel(
            name="ExperimentMetric",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("metric_type", models.CharField(db_index=True, max_length=80)),
                ("value", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ("unit", models.CharField(blank=True, max_length=30)),
                ("source_component", models.CharField(blank=True, db_index=True, max_length=80)),
                ("source_reference", models.CharField(blank=True, db_index=True, max_length=180)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("recorded_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="metrics", to="ai_experimentation_framework.experimentassignment")),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_experiment_metrics", to="companies.company")),
                ("experiment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="ai_experimentation_framework.experiment")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_experiment_metrics", to="smart_system.operationalsite")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="ai_experimentation_framework.variant")),
            ],
            options={"db_table": "ai_experimentation_metrics", "ordering": ["-recorded_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ExperimentResult",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("summary", models.TextField(blank=True)),
                ("primary_metric", models.CharField(blank=True, max_length=80)),
                ("confidence_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=20)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("recommendation", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("experiment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="ai_experimentation_framework.experiment")),
                ("winning_variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="result_wins", to="ai_experimentation_framework.variant")),
            ],
            options={"db_table": "ai_experimentation_results", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ExperimentAuditTrail",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=80)),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_experiment_audit_entries", to=settings.AUTH_USER_MODEL)),
                ("experiment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_entries", to="ai_experimentation_framework.experiment")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_entries", to="ai_experimentation_framework.variant")),
            ],
            options={"db_table": "ai_experimentation_audit_trail", "ordering": ["created_at", "id"]},
        ),
        migrations.RunPython(seed_experiment_policy, migrations.RunPython.noop),
    ]
