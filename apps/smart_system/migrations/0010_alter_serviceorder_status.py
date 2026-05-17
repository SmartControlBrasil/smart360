from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("smart_system", "0009_maintenance_contracts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="serviceorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("scheduled", "Scheduled"),
                    ("in_progress", "In Progress"),
                    ("waiting_quote_approval", "Waiting Quote Approval"),
                    ("waiting_parts", "Waiting Parts"),
                    ("on_hold", "On Hold"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="open",
                max_length=32,
            ),
        ),
    ]
