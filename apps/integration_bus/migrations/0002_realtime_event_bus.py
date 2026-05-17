from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_realtime_subscriptions(apps, schema_editor):
    EventSubscription = apps.get_model("integration_bus", "EventSubscription")
    Policy = apps.get_model("ai_policy_studio", "Policy")
    PolicyScope = apps.get_model("ai_policy_studio", "PolicyScope")
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")

    subscriptions = [
        ("failures.created", "ai_agents_center", "reactive_agent_trigger"),
        ("work_orders.delayed", "ai_agents_center", "reactive_agent_trigger"),
        ("billing.invoice_overdue", "ai_agents_center", "reactive_agent_trigger"),
        ("marketplace.request_created", "ai_agents_center", "reactive_agent_trigger"),
        ("inventory.low_stock_detected", "ai_agents_center", "reactive_agent_trigger"),
        ("decision.awaiting_approval", "executive_war_room", "realtime_update"),
        ("agents.recommendation_created", "executive_war_room", "realtime_update"),
        ("agents.anomaly_detected", "executive_war_room", "realtime_update"),
        ("simulation.completed", "executive_war_room", "realtime_update"),
        ("autonomy.execution_completed", "executive_war_room", "realtime_update"),
        ("autonomy.execution_failed", "executive_war_room", "realtime_update"),
        ("decision.awaiting_approval", "briefings", "briefing_refresh"),
        ("failures.created", "briefings", "briefing_refresh"),
        ("decision.awaiting_approval", "copilot_context", "copilot_context_refresh"),
    ]
    for event_name, target_module, handler_name in subscriptions:
        EventSubscription.objects.update_or_create(
            event_name=event_name,
            target_module=target_module,
            handler_name=handler_name,
            defaults={
                "is_active": True,
                "execution_mode": "async",
                "retry_policy": {"max_retries": 3},
            },
        )

    policy, _ = Policy.objects.update_or_create(
        slug="global-reactive-event-governance",
        defaults={
            "name": "Global Reactive Event Governance",
            "description": "Controla triggers reativos do barramento de eventos.",
            "tenant_scope": "global",
            "is_global": True,
            "status": "active",
            "version": 1,
        },
    )
    PolicyScope.objects.update_or_create(
        policy=policy,
        company=None,
        site=None,
        module_slug="integration_bus",
        action_type="",
        agent_slug="",
        copilot_key="",
        defaults={"priority": 50},
    )
    for action_type, result in [
        ("event_to_agent_trigger", "allow"),
        ("event_to_briefing_refresh", "allow"),
        ("event_to_dashboard_update", "allow"),
        ("event_to_copilot_refresh", "allow"),
        ("event_to_notification_candidate", "require_approval"),
        ("event_to_autonomy_candidate", "require_approval"),
    ]:
        PolicyRule.objects.update_or_create(
            policy=policy,
            action_type=action_type,
            risk_level="any",
            defaults={
                "result": result,
                "allowed": result != "deny",
                "requires_approval": result == "require_approval",
                "autonomy_level": 1,
                "approver_roles": ["company-admin", "super-admin"] if result == "require_approval" else [],
                "rationale": f"Reactive trigger policy for {action_type}.",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        ("integration_bus", "0001_initial"),
        ("ai_policy_studio", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationevent",
            name="company",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="integration_events", to="companies.company"),
        ),
        migrations.AddField(
            model_name="integrationevent",
            name="event_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="integrationevent",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="integrationevent",
            name="priority",
            field=models.CharField(choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("critical", "Critical")], db_index=True, default="normal", max_length=20),
        ),
        migrations.AddField(
            model_name="integrationevent",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="integrationevent",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="integration_events", to="smart_system.operationalsite"),
        ),
        migrations.AddIndex(
            model_name="integrationevent",
            index=models.Index(fields=["event_name", "priority", "occurred_at"], name="integration_event_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationevent",
            index=models.Index(fields=["company", "site", "occurred_at"], name="integration_event_scope_idx"),
        ),
        migrations.CreateModel(
            name="EventDelivery",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("subscriber_name", models.CharField(db_index=True, max_length=160)),
                ("delivery_status", models.CharField(choices=[("pending", "Pending"), ("delivered", "Delivered"), ("failed", "Failed"), ("retrying", "Retrying"), ("skipped", "Skipped"), ("dead_letter", "Dead Letter")], db_index=True, default="pending", max_length=20)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("delivery_payload", models.JSONField(blank=True, default=dict)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("integration_event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="integration_bus.integrationevent")),
                ("subscription", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deliveries", to="integration_bus.eventsubscription")),
            ],
            options={"db_table": "integration_event_deliveries", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="eventdelivery",
            constraint=models.UniqueConstraint(fields=("integration_event", "subscriber_name"), name="uniq_integration_event_delivery"),
        ),
        migrations.CreateModel(
            name="ReactiveTriggerLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("target_component", models.CharField(db_index=True, max_length=120)),
                ("trigger_type", models.CharField(choices=[("event_to_agent_trigger", "Event To Agent Trigger"), ("event_to_briefing_refresh", "Event To Briefing Refresh"), ("event_to_dashboard_update", "Event To Dashboard Update"), ("event_to_autonomy_candidate", "Event To Autonomy Candidate"), ("event_to_notification_candidate", "Event To Notification Candidate"), ("event_to_copilot_refresh", "Event To Copilot Refresh")], db_index=True, max_length=40)),
                ("trigger_status", models.CharField(choices=[("pending", "Pending"), ("fired", "Fired"), ("skipped", "Skipped"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("summary", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("integration_event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactive_triggers", to="integration_bus.integrationevent")),
            ],
            options={"db_table": "integration_reactive_trigger_logs", "ordering": ["-created_at"]},
        ),
        migrations.RunPython(seed_realtime_subscriptions, migrations.RunPython.noop),
    ]
