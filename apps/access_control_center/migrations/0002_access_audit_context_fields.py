from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0002_multitenant_scope"),
        ("access_control_center", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accessauditlog",
            name="after_state",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="before_state",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="access_audit_logs",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="correlation_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="origin",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="accessauditlog",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="access_audit_logs",
                to="smart_system.operationalsite",
            ),
        ),
    ]
