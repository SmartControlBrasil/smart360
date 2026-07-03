from django.db import migrations

def seed_commercial_policies(apps, schema_editor):
    DecisionPolicy = apps.get_model("ai_decision_engine", "DecisionPolicy")
    policies = [
        {
            "slug": "decision-review-commercial-opportunity",
            "name": "Review Commercial Opportunity",
            "description": "Revisao de oportunidade comercial do Atlas.",
            "action_type": "review_commercial_opportunity",
            "risk_level": "medium",
            "autonomy_level": 1,
            "requires_human_approval": True,
            "enabled": True,
            "tenant_scope_mode": "company",
            "approver_role_slugs": ["commercial-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
        {
            "slug": "decision-enrich-commercial-opportunity",
            "name": "Enrich Commercial Opportunity",
            "description": "Enriquecimento de oportunidade comercial do Atlas.",
            "action_type": "enrich_commercial_opportunity",
            "risk_level": "low",
            "autonomy_level": 2,
            "requires_human_approval": False,
            "enabled": True,
            "tenant_scope_mode": "company",
            "approver_role_slugs": ["commercial-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "auto"},
        },
        {
            "slug": "decision-convert-commercial-opportunity-to-lead",
            "name": "Convert Commercial Opportunity to Lead",
            "description": "Converte oportunidade comercial aprovada em Lead oficial.",
            "action_type": "convert_commercial_opportunity_to_lead",
            "risk_level": "high",
            "autonomy_level": 1,
            "requires_human_approval": True,
            "enabled": True,
            "tenant_scope_mode": "company",
            "approver_role_slugs": ["commercial-manager", "company-admin", "super-admin"],
            "config": {"auto_execute": True, "execution_mode": "after_approval"},
        },
    ]
    for item in policies:
        DecisionPolicy.objects.update_or_create(slug=item["slug"], defaults=item)

def remove_commercial_policies(apps, schema_editor):
    DecisionPolicy = apps.get_model("ai_decision_engine", "DecisionPolicy")
    slugs = [
        "decision-review-commercial-opportunity",
        "decision-enrich-commercial-opportunity",
        "decision-convert-commercial-opportunity-to-lead",
    ]
    DecisionPolicy.objects.filter(slug__in=slugs).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("ai_decision_engine", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_commercial_policies, remove_commercial_policies),
    ]
