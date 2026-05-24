# Generated manually for SaaS company registration fields.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="city",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="company",
            name="state",
            field=models.CharField(
                blank=True,
                max_length=80,
                help_text="UF ou estado/regiao conforme o documento cadastrado.",
            ),
        ),
    ]
