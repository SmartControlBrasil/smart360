from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_autonomous_defaults(apps, schema_editor):
    AutonomousModeConfig = apps.get_model("ai_autonomous_ops", "AutonomousModeConfig")
    AutonomousExecutionGuard = apps.get_model("ai_autonomous_ops", "AutonomousExecutionGuard")
    Policy = apps.get_model("ai_policy_studio", "Policy")
    PolicyScope = apps.get_model("ai_policy_studio", "PolicyScope")
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")

    AutonomousModeConfig.objects.get_or_create(
        company=None,
        defaults={
            "is_enabled": True,
            "mode_level": 2,
            "max_risk_level": "medium",
            "allowed_action_types": ["mark_asset_attention", "create_investigation_task", "flag_contract_profitability_attention", "reorder_route_proposal"],
            "blocked_action_types": ["create_work_order_proposal", "assign_marketplace_candidate_proposal"],
            "requires_simulation_for": ["reorder_route_proposal"],
            "confidence_threshold_default": "0.80",
            "max_executions_per_hour": 30,
            "max_executions_per_day": 200,
            "max_failures_per_day": 5,
            "max_rollbacks_per_day": 5,
        },
    )
    for guard in [
        {"guard_type": "confidence", "threshold_key": "reorder_route_proposal", "threshold_value": "0.85"},
        {"guard_type": "volume", "threshold_key": "max_executions_per_hour", "threshold_value": "30"},
        {"guard_type": "failure_rate", "threshold_key": "max_failures_per_day", "threshold_value": "5"},
    ]:
        AutonomousExecutionGuard.objects.get_or_create(company=None, guard_type=guard["guard_type"], threshold_key=guard["threshold_key"], defaults={"threshold_value": guard["threshold_value"], "enabled": True})

    policy, _ = Policy.objects.get_or_create(
        slug="global-autonomy-governance",
        defaults={
            "name": "Global Autonomy Governance",
            "description": "Governanca do modo autonomo supervisionado.",
            "tenant_scope": "global",
            "is_global": True,
            "status": "active",
            "version": 1,
        },
    )
    PolicyScope.objects.get_or_create(policy=policy, company=None, site=None, module_slug="ai_autonomous_ops", defaults={"priority": 20})
    rules = [
        ("evaluate_candidate", "low", "allow", False, True, []),
        ("execute_autonomy", "any", "allow", False, True, []),
        ("rollback_autonomy", "medium", "allow", False, True, ["maintenance-manager", "company-admin", "super-admin"]),
        ("kill_switch", "high", "require_approval", True, True, ["company-admin", "super-admin"]),
    ]
    for action_type, risk, result, requires_approval, allowed, approver_roles in rules:
        PolicyRule.objects.get_or_create(
            policy=policy,
            action_type=action_type,
            risk_level=risk,
            defaults={
                "autonomy_level": 1,
                "requires_approval": requires_approval,
                "allowed": allowed,
                "result": result,
                "approver_roles": approver_roles,
                "conditions": {},
                "rationale": f"Autonomous mode rule for {action_type}.",
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        ("ai_decision_engine", "0001_initial"),
        ("ai_simulation_engine", "0001_initial"),
        ("ai_policy_studio", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutonomousModeConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_enabled", models.BooleanField(default=False)),
                ("mode_level", models.PositiveSmallIntegerField(default=1)),
                ("max_risk_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="low", max_length=20)),
                ("allowed_action_types", models.JSONField(blank=True, default=list)),
                ("blocked_action_types", models.JSONField(blank=True, default=list)),
                ("requires_simulation_for", models.JSONField(blank=True, default=list)),
                ("confidence_threshold_default", models.DecimalField(decimal_places=2, default=0.8, max_digits=5)),
                ("confidence_threshold_overrides", models.JSONField(blank=True, default=dict)),
                ("max_executions_per_hour", models.PositiveIntegerField(default=30)),
                ("max_executions_per_day", models.PositiveIntegerField(default=200)),
                ("max_failures_per_day", models.PositiveIntegerField(default=5)),
                ("max_rollbacks_per_day", models.PositiveIntegerField(default=5)),
                ("kill_switch_enabled", models.BooleanField(default=False)),
                ("kill_switch_action_types", models.JSONField(blank=True, default=list)),
                ("kill_switch_agents", models.JSONField(blank=True, default=list)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="autonomous_mode_configs", to="companies.company")),
            ],
            options={"db_table": "ai_autonomous_mode_configs", "ordering": ["company_id", "-updated_at"]},
        ),
        migrations.CreateModel(
            name="AutonomousExecutionGuard",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("guard_type", models.CharField(choices=[("volume", "Volume"), ("failure_rate", "Failure Rate"), ("rollback_rate", "Rollback Rate"), ("confidence", "Confidence"), ("incident", "Incident"), ("kill_switch", "Kill Switch")], db_index=True, max_length=30)),
                ("threshold_key", models.CharField(db_index=True, max_length=80)),
                ("threshold_value", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("enabled", models.BooleanField(default=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="autonomous_guards", to="companies.company")),
            ],
            options={"db_table": "ai_autonomous_execution_guards", "ordering": ["company_id", "guard_type", "threshold_key"]},
        ),
        migrations.CreateModel(
            name="AutonomousExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action_type", models.CharField(db_index=True, max_length=80)),
                ("source_agent", models.CharField(blank=True, db_index=True, max_length=120)),
                ("risk_level", models.CharField(db_index=True, max_length=20)),
                ("confidence_level", models.CharField(blank=True, max_length=20)),
                ("confidence_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("execution_status", models.CharField(choices=[("candidate", "Candidate"), ("blocked", "Blocked"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("rolled_back", "Rolled Back")], db_index=True, default="candidate", max_length=20)),
                ("execution_summary", models.TextField(blank=True)),
                ("rollback_supported", models.BooleanField(default=False)),
                ("rollback_status", models.CharField(choices=[("not_required", "Not Required"), ("available", "Available"), ("executed", "Executed"), ("failed", "Failed")], default="not_required", max_length=20)),
                ("policy_snapshot", models.JSONField(blank=True, default=dict)),
                ("guard_snapshot", models.JSONField(blank=True, default=dict)),
                ("expected_outcome", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="autonomous_executions", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autonomous_executions", to="smart_system.operationalsite")),
                ("source_decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autonomous_executions", to="ai_decision_engine.agentdecision")),
                ("source_simulation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autonomous_executions", to="ai_simulation_engine.simulationrun")),
            ],
            options={"db_table": "ai_autonomous_executions", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AutonomousIncident",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], db_index=True, default="medium", max_length=20)),
                ("incident_type", models.CharField(db_index=True, max_length=80)),
                ("summary", models.TextField()),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")], db_index=True, default="open", max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("autonomous_execution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="incidents", to="ai_autonomous_ops.autonomousexecution")),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="autonomous_incidents", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autonomous_incidents", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_autonomous_incidents", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AutonomousAuditTrail",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=80)),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autonomous_audit_entries", to=settings.AUTH_USER_MODEL)),
                ("autonomous_execution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_entries", to="ai_autonomous_ops.autonomousexecution")),
            ],
            options={"db_table": "ai_autonomous_audit_trail", "ordering": ["created_at", "id"]},
        ),
        migrations.RunPython(seed_autonomous_defaults, migrations.RunPython.noop),
    ]

