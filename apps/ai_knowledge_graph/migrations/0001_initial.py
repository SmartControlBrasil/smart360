import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def seed_graph_subscriptions(apps, schema_editor):
    EventSubscription = apps.get_model("integration_bus", "EventSubscription")
    subscriptions = [
        ("failures.created", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("work_orders.created", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("work_orders.completed", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("preventive.completed", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("preventive.overdue", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("inventory.adjusted", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("inventory.consumed", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("marketplace.assignment_created", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("agents.recommendation_created", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("decision.executed", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
        ("autonomy.execution_completed", "ai_knowledge_graph", "knowledge_graph_projection_refresh"),
    ]
    for event_name, target_module, handler_name in subscriptions:
        EventSubscription.objects.update_or_create(
            event_name=event_name,
            target_module=target_module,
            handler_name=handler_name,
            defaults={"is_active": True, "execution_mode": "async", "retry_policy": {"max_retries": 3}},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        ("integration_bus", "0002_realtime_event_bus"),
        ("marketplace_technicians", "0001_initial"),
        ("ai_agents_center", "0001_initial"),
        ("ai_decision_engine", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GraphNode",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("node_type", models.CharField(choices=[("asset", "Asset"), ("asset_category", "Asset Category"), ("failure_event", "Failure Event"), ("failure_mode", "Failure Mode"), ("rca_cause", "RCA Cause"), ("preventive_plan", "Preventive Plan"), ("work_order", "Work Order"), ("checklist", "Checklist"), ("checklist_item", "Checklist Item"), ("part", "Part"), ("technician", "Technician"), ("skill", "Skill"), ("company", "Company"), ("site", "Site"), ("contract", "Contract"), ("quote", "Quote"), ("report", "Report"), ("recommendation", "Recommendation"), ("decision", "Decision"), ("anomaly", "Anomaly"), ("service_request", "Service Request"), ("assignment", "Assignment")], db_index=True, max_length=40)),
                ("source_type", models.CharField(db_index=True, max_length=80)),
                ("source_id", models.CharField(db_index=True, max_length=120)),
                ("label", models.CharField(max_length=255)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("strength", models.DecimalField(decimal_places=2, default=1, max_digits=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="graph_nodes", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="graph_nodes", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_knowledge_graph_nodes", "ordering": ["node_type", "label"]},
        ),
        migrations.AddConstraint(
            model_name="graphnode",
            constraint=models.UniqueConstraint(fields=("company", "node_type", "source_type", "source_id"), name="uniq_knowledge_graph_node_source"),
        ),
        migrations.AddIndex(
            model_name="graphnode",
            index=models.Index(fields=["company", "site", "node_type"], name="knowledge_graph_node_scope_idx"),
        ),
        migrations.CreateModel(
            name="GraphProjectionRun",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("projection_type", models.CharField(choices=[("full_projection", "Full Projection"), ("event_refresh", "Event Refresh"), ("targeted_projection", "Targeted Projection")], db_index=True, max_length=40)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("summary", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="graph_projection_runs", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="graph_projection_runs", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_knowledge_graph_projection_runs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GraphEdge",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("edge_type", models.CharField(choices=[("asset_located_at_site", "Asset Located At Site"), ("asset_belongs_to_category", "Asset Belongs To Category"), ("asset_has_failure", "Asset Has Failure"), ("failure_has_mode", "Failure Has Mode"), ("failure_has_cause", "Failure Has Cause"), ("work_order_targets_asset", "Work Order Targets Asset"), ("work_order_generated_from_failure", "Work Order Generated From Failure"), ("preventive_targets_asset", "Preventive Targets Asset"), ("checklist_used_in_work_order", "Checklist Used In Work Order"), ("checklist_item_flagged_issue", "Checklist Item Flagged Issue"), ("part_used_in_work_order", "Part Used In Work Order"), ("part_related_to_asset", "Part Related To Asset"), ("technician_has_skill", "Technician Has Skill"), ("technician_executed_work_order", "Technician Executed Work Order"), ("technician_best_fit_for_category", "Technician Best Fit For Category"), ("contract_covers_asset", "Contract Covers Asset"), ("company_owns_site", "Company Owns Site"), ("company_has_contract", "Company Has Contract"), ("recommendation_targets_asset", "Recommendation Targets Asset"), ("decision_acts_on_entity", "Decision Acts On Entity"), ("anomaly_detected_on_entity", "Anomaly Detected On Entity"), ("assignment_allocates_technician", "Assignment Allocates Technician"), ("service_request_targets_asset", "Service Request Targets Asset"), ("service_request_linked_to_site", "Service Request Linked To Site"), ("similar_context", "Similar Context")], db_index=True, max_length=60)),
                ("weight", models.DecimalField(decimal_places=2, default=1, max_digits=8)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="graph_edges", to="companies.company")),
                ("from_node", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_edges", to="ai_knowledge_graph.graphnode")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="graph_edges", to="smart_system.operationalsite")),
                ("to_node", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_edges", to="ai_knowledge_graph.graphnode")),
            ],
            options={"db_table": "ai_knowledge_graph_edges", "ordering": ["-weight", "edge_type"]},
        ),
        migrations.AddConstraint(
            model_name="graphedge",
            constraint=models.UniqueConstraint(fields=("company", "edge_type", "from_node", "to_node"), name="uniq_knowledge_graph_edge"),
        ),
        migrations.AddIndex(
            model_name="graphedge",
            index=models.Index(fields=["company", "site", "edge_type"], name="knowledge_graph_edge_scope_idx"),
        ),
        migrations.RunPython(seed_graph_subscriptions, migrations.RunPython.noop),
    ]

