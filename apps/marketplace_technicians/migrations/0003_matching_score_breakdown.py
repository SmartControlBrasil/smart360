from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace_technicians", "0002_offers_and_marketplace_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="calculation_context",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="distance_km",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="ranking_position",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_availability",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_distance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_experience",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_rating",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_response_time",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="score_specialty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="technicianmatchingrecord",
            name="scoring_version",
            field=models.CharField(default="v1", max_length=32),
        ),
    ]
