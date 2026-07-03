from django.db import migrations

def seed_commercial_rules(apps, schema_editor):
    Policy = apps.get_model("ai_policy_studio", "Policy")
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")

    try:
        policy = Policy.objects.get(slug="global-decision-governance")
    except Policy.DoesNotExist:
        # Fallback if policy is not seeded in some test runs
        return

    rules = [
        {
            "action_type": "enrich_commercial_opportunity",
            "risk_level": "low",
            "autonomy_level": 2,
            "requires_approval": False,
            "allowed": True,
            "result": "allow",
            "approver_roles": ["commercial-manager", "company-admin", "super-admin"],
            "rationale": "Deterministic enrichment of commercial opportunities.",
        },
        {
            "action_type": "review_commercial_opportunity",
            "risk_level": "medium",
            "autonomy_level": 1,
            "requires_approval": True,
            "allowed": True,
            "result": "require_approval",
            "approver_roles": ["commercial-manager", "company-admin", "super-admin"],
            "rationale": "Review of commercial opportunity requires human manager approval.",
        },
        {
            "action_type": "convert_commercial_opportunity_to_lead",
            "risk_level": "high",
            "autonomy_level": 1,
            "requires_approval": True,
            "allowed": True,
            "result": "require_approval",
            "approver_roles": ["commercial-manager", "company-admin", "super-admin"],
            "rationale": "Lead conversion requires human manager approval.",
        },
    ]

    for item in rules:
        PolicyRule.objects.update_or_create(
            policy=policy,
            action_type=item["action_type"],
            defaults=item,
        )

def remove_commercial_rules(apps, schema_editor):
    PolicyRule = apps.get_model("ai_policy_studio", "PolicyRule")
    action_types = [
        "enrich_commercial_opportunity",
        "review_commercial_opportunity",
        "convert_commercial_opportunity_to_lead",
    ]
    PolicyRule.objects.filter(action_type__in=action_types).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ai_policy_studio", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_commercial_rules, remove_commercial_rules),
    ]
