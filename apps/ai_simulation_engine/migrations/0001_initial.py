from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_simulation_types(apps, schema_editor):
    SimulationType = apps.get_model("ai_simulation_engine", "SimulationType")
    items = [
        ("route_reorder_simulation", "Route Reorder Simulation", "Compara ordem atual vs ordem proposta da rota.", "recommended"),
        ("technician_reassignment_simulation", "Technician Reassignment Simulation", "Simula troca de tecnico entre visitas ou OS.", "recommended"),
        ("preventive_frequency_change_simulation", "Preventive Frequency Change Simulation", "Simula mudanca de frequencia preventiva.", "required"),
        ("contract_repricing_simulation", "Contract Repricing Simulation", "Simula reajuste contratual e margem projetada.", "required"),
        ("route_consolidation_simulation", "Route Consolidation Simulation", "Simula consolidacao regional de visitas.", "recommended"),
        ("workload_redistribution_simulation", "Workload Redistribution Simulation", "Simula redistribuicao de carga entre tecnicos.", "recommended"),
        ("marketplace_candidate_swap_simulation", "Marketplace Candidate Swap Simulation", "Simula troca do candidato marketplace.", "recommended"),
        ("maintenance_action_plan_simulation", "Maintenance Action Plan Simulation", "Simula plano de manutencao/preventiva extraordinaria.", "required"),
    ]
    for slug, name, description, policy_mode in items:
        SimulationType.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "enabled": True,
                "policy_mode": policy_mode,
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0009_maintenance_contracts"),
        ("ai_decision_engine", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SimulationType",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("enabled", models.BooleanField(default=True)),
                ("policy_mode", models.CharField(choices=[("optional", "Optional"), ("recommended", "Recommended"), ("required", "Required")], default="optional", max_length=20)),
                ("heuristics_config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ai_simulation_types", "ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="SimulationScenario",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=220)),
                ("description", models.TextField(blank=True)),
                ("target_entity", models.CharField(blank=True, db_index=True, max_length=80)),
                ("target_entity_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="simulation_scenarios", to="companies.company")),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="simulation_scenarios_created", to=settings.AUTH_USER_MODEL)),
                ("simulation_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="scenarios", to="ai_simulation_engine.simulationtype")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="simulation_scenarios", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_simulation_scenarios", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SimulationRun",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("trigger_type", models.CharField(choices=[("manual", "Manual"), ("decision", "Decision"), ("agent", "Agent"), ("copilot", "Copilot"), ("api", "API")], default="manual", max_length=20)),
                ("source_type", models.CharField(choices=[("decision", "Decision"), ("proposal", "Proposal"), ("copilot", "Copilot"), ("agent", "Agent"), ("direct", "Direct")], default="direct", max_length=20)),
                ("source_reference", models.CharField(blank=True, db_index=True, max_length=180)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("baseline_snapshot", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("request_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="simulation_runs_requested", to=settings.AUTH_USER_MODEL)),
                ("decision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="simulation_runs", to="ai_decision_engine.agentdecision")),
                ("scenario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="ai_simulation_engine.simulationscenario")),
            ],
            options={"db_table": "ai_simulation_runs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SimulationResult",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("summary", models.TextField()),
                ("impact_score", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("confidence_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=20)),
                ("risk_delta", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("cost_delta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sla_delta", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("profit_delta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("travel_delta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("workload_delta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("recommendation", models.TextField(blank=True)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("simulation_run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="ai_simulation_engine.simulationrun")),
            ],
            options={"db_table": "ai_simulation_results", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SimulationAuditTrail",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=80)),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="simulation_audit_entries", to=settings.AUTH_USER_MODEL)),
                ("simulation_run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_entries", to="ai_simulation_engine.simulationrun")),
            ],
            options={"db_table": "ai_simulation_audit_trail", "ordering": ["created_at", "id"]},
        ),
        migrations.RunPython(seed_simulation_types, migrations.RunPython.noop),
    ]

