from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_policy_studio(apps, schema_editor):
    Policy = apps.get_model("ai_policy_studio", "Policy")
    PolicyScope = apps.get_model("ai_policy_studio", "PolicyScope")
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")

    seeds = [
        {
            "policy": {
                "slug": "global-decision-governance",
                "name": "Global Decision Governance",
                "description": "Governanca padrao para Decision Engine.",
                "tenant_scope": "global",
                "is_global": True,
                "status": "active",
                "version": 1,
            },
            "scope": {"module_slug": "ai_decision_engine", "priority": 10},
            "rules": [
                {
                    "action_type": "",
                    "risk_level": "any",
                    "autonomy_level": 1,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Fallback decision governance requires supervised approval by default.",
                },
                {
                    "action_type": "mark_asset_attention",
                    "risk_level": "low",
                    "autonomy_level": 2,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["maintenance-manager", "company-admin", "super-admin"],
                    "rationale": "Safe non-destructive asset attention flag.",
                },
                {
                    "action_type": "create_work_order_proposal",
                    "risk_level": "high",
                    "autonomy_level": 1,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["maintenance-manager", "company-admin", "super-admin"],
                    "rationale": "Work order creation requires governance review.",
                },
                {
                    "action_type": "create_investigation_task",
                    "risk_level": "low",
                    "autonomy_level": 2,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["maintenance-manager", "company-admin", "super-admin"],
                    "rationale": "Low-risk investigations remain allowed under supervision logs.",
                },
                {
                    "action_type": "flag_contract_profitability_attention",
                    "risk_level": "medium",
                    "autonomy_level": 2,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["commercial-manager", "company-admin", "super-admin"],
                    "rationale": "Non-destructive profitability attention flags remain allowed.",
                },
                {
                    "action_type": "",
                    "risk_level": "critical",
                    "autonomy_level": 0,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "escalate",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Critical actions always escalate.",
                },
            ],
        },
        {
            "policy": {
                "slug": "global-agent-governance",
                "name": "Global Agent Governance",
                "description": "Run permission and action proposal guardrails for agents.",
                "tenant_scope": "global",
                "is_global": True,
                "status": "active",
                "version": 1,
            },
            "scope": {"module_slug": "ai_agents_center", "priority": 20},
            "rules": [
                {
                    "action_type": "run_agent",
                    "risk_level": "any",
                    "autonomy_level": 1,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Agents may run when access control permits.",
                },
                {
                    "action_type": "",
                    "risk_level": "any",
                    "autonomy_level": 1,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Fallback proposal governance allows routing into Decision Engine.",
                },
                {
                    "action_type": "assign_marketplace_candidate_proposal",
                    "risk_level": "high",
                    "autonomy_level": 1,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["coordinator", "company-admin", "super-admin"],
                    "rationale": "Marketplace assignments remain human supervised.",
                },
            ],
        },
        {
            "policy": {
                "slug": "global-optimization-governance",
                "name": "Global Optimization Governance",
                "description": "Optimization adjustments require explicit governance.",
                "tenant_scope": "global",
                "is_global": True,
                "status": "active",
                "version": 1,
            },
            "scope": {"module_slug": "ai_optimization_loop", "priority": 30},
            "rules": [
                {
                    "action_type": "",
                    "risk_level": "any",
                    "autonomy_level": 0,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Optimization changes are supervised by default.",
                },
                {
                    "action_type": "approval_requirement_adjustment",
                    "risk_level": "high",
                    "autonomy_level": 0,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["company-admin", "super-admin"],
                    "rationale": "Approval changes need governance.",
                },
                {
                    "action_type": "heuristic_config_adjustment",
                    "risk_level": "medium",
                    "autonomy_level": 0,
                    "requires_approval": True,
                    "allowed": True,
                    "result": "require_approval",
                    "approver_roles": ["maintenance-manager", "company-admin", "super-admin"],
                    "rationale": "Simulation heuristic changes stay supervised.",
                },
            ],
        },
        {
            "policy": {
                "slug": "global-simulation-governance",
                "name": "Global Simulation Governance",
                "description": "Baseline governance for simulation engine.",
                "tenant_scope": "global",
                "is_global": True,
                "status": "active",
                "version": 1,
            },
            "scope": {"module_slug": "ai_simulation_engine", "priority": 25},
            "rules": [
                {
                    "action_type": "",
                    "risk_level": "any",
                    "autonomy_level": 1,
                    "requires_approval": False,
                    "allowed": True,
                    "result": "allow",
                    "approver_roles": ["maintenance-manager", "company-admin", "super-admin"],
                    "rationale": "Simulation is allowed by default when requested through governed flows.",
                },
            ],
        },
    ]
    for item in seeds:
        policy, _ = Policy.objects.update_or_create(slug=item["policy"]["slug"], defaults=item["policy"])
        PolicyScope.objects.get_or_create(policy=policy, **item["scope"])
        for rule in item["rules"]:
            PolicyRule.objects.get_or_create(
                policy=policy,
                action_type=rule["action_type"],
                risk_level=rule["risk_level"],
                result=rule["result"],
                defaults=rule,
            )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0002_sitemembership"),
        ("smart_system", "0009_maintenance_contracts"),
    ]

    operations = [
        migrations.CreateModel(
            name="Policy",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("tenant_scope", models.CharField(db_index=True, default="global", max_length=20)),
                ("is_global", models.BooleanField(default=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_policies_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ai_policy_studio_policies", "ordering": ["name", "created_at"]},
        ),
        migrations.CreateModel(
            name="PolicyEvaluation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("module_slug", models.CharField(blank=True, db_index=True, max_length=80)),
                ("action_type", models.CharField(blank=True, db_index=True, max_length=80)),
                ("result", models.CharField(db_index=True, max_length=30)),
                ("reason", models.TextField(blank=True)),
                ("context_payload", models.JSONField(blank=True, default=dict)),
                ("evaluated_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="policy_studio_evaluations", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_evaluations", to="smart_system.operationalsite")),
                ("policy", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evaluations", to="ai_policy_studio.policy")),
            ],
            options={"db_table": "ai_policy_studio_evaluations", "ordering": ["-evaluated_at"]},
        ),
        migrations.CreateModel(
            name="PolicyRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action_type", models.CharField(blank=True, db_index=True, max_length=80)),
                ("risk_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"), ("any", "Any")], db_index=True, default="any", max_length=20)),
                ("autonomy_level", models.PositiveIntegerField(default=0)),
                ("requires_approval", models.BooleanField(default=False)),
                ("allowed", models.BooleanField(default=True)),
                ("result", models.CharField(choices=[("allow", "Allow"), ("deny", "Deny"), ("require_approval", "Require Approval"), ("escalate", "Escalate")], db_index=True, default="allow", max_length=30)),
                ("approver_roles", models.JSONField(blank=True, default=list)),
                ("conditions", models.JSONField(blank=True, default=dict)),
                ("rationale", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="ai_policy_studio.policy")),
            ],
            options={"db_table": "ai_policy_studio_rules", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="PolicyScope",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("module_slug", models.CharField(blank=True, db_index=True, max_length=80)),
                ("action_type", models.CharField(blank=True, db_index=True, max_length=80)),
                ("agent_slug", models.CharField(blank=True, db_index=True, max_length=80)),
                ("copilot_key", models.CharField(blank=True, db_index=True, max_length=80)),
                ("priority", models.PositiveIntegerField(db_index=True, default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="policy_studio_scopes", to="companies.company")),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scopes", to="ai_policy_studio.policy")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_scopes", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_policy_studio_scopes", "ordering": ["priority", "id"]},
        ),
        migrations.CreateModel(
            name="PolicySimulationRun",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="policy_studio_simulations", to="companies.company")),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_simulations_created", to=settings.AUTH_USER_MODEL)),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="simulation_runs", to="ai_policy_studio.policy")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_simulations", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_policy_studio_simulation_runs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PolicyVersion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("version_number", models.PositiveIntegerField()),
                ("snapshot", models.JSONField(blank=True, default=dict)),
                ("change_summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="policy_studio_versions_created", to=settings.AUTH_USER_MODEL)),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="ai_policy_studio.policy")),
            ],
            options={"db_table": "ai_policy_studio_versions", "ordering": ["-version_number", "-created_at"], "unique_together": {("policy", "version_number")}},
        ),
        migrations.AddField(
            model_name="policyevaluation",
            name="rule",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evaluations", to="ai_policy_studio.policyrule"),
        ),
        migrations.RunPython(seed_policy_studio, migrations.RunPython.noop),
    ]
