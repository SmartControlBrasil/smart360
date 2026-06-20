# Generated manually — rename EDU/Eduardo para Atlas sem perder dados.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rename_commercial_agent(apps, schema_editor):
    AgentDefinition = apps.get_model("ai_agents_center", "AgentDefinition")
    agents = AgentDefinition.objects.filter(slug="eduardo-commercial-intelligence-agent")
    for agent in agents:
        agent.slug = "atlas-commercial-intelligence-agent"
        agent.name = "Atlas Commercial Intelligence Agent"
        config = dict(agent.config or {})
        if config.get("prompt_reference") == "knowledge/comercial/agente_eduardo.md":
            config["prompt_reference"] = "knowledge/comercial/agente_atlas.md"
        agent.config = config
        agent.save(update_fields=["slug", "name", "config", "updated_at"])


def revert_commercial_agent(apps, schema_editor):
    AgentDefinition = apps.get_model("ai_agents_center", "AgentDefinition")
    agents = AgentDefinition.objects.filter(slug="atlas-commercial-intelligence-agent")
    for agent in agents:
        agent.slug = "eduardo-commercial-intelligence-agent"
        agent.name = "Eduardo Commercial Intelligence Agent"
        config = dict(agent.config or {})
        if config.get("prompt_reference") == "knowledge/comercial/agente_atlas.md":
            config["prompt_reference"] = "knowledge/comercial/agente_eduardo.md"
        agent.config = config
        agent.save(update_fields=["slug", "name", "config", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("ai_agents_center", "0014_edu_prospect_import_and_outreach"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="EduardoProspectImportBatch",
            new_name="AtlasProspectImportBatch",
        ),
        migrations.AlterModelTable(
            name="atlasprospectimportbatch",
            table="ai_agents_atlas_prospect_import_batches",
        ),
        migrations.RenameIndex(
            model_name="atlasprospectimportbatch",
            new_name="ai_atl_imp_stat_crt_idx",
            old_name="ai_edu_imp_status_created_idx",
        ),
        migrations.RenameIndex(
            model_name="atlasprospectimportbatch",
            new_name="ai_atl_imp_src_crt_idx",
            old_name="ai_edu_imp_source_created_idx",
        ),
        migrations.AlterField(
            model_name="atlasprospectimportbatch",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="atlas_prospect_import_batches",
                to="companies.company",
            ),
        ),
        migrations.AlterField(
            model_name="atlasprospectimportbatch",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="atlas_prospect_import_batches",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(rename_commercial_agent, revert_commercial_agent),
    ]
