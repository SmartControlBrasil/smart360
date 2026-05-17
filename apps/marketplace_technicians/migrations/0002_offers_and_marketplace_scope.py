import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("marketplace_technicians", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="technicianprofile",
            name="certifications",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="technicianprofile",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="technician_profiles",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="technicianprofile",
            name="service_radius_km",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="technicianservicerequest",
            name="category",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="technicianservicerequest",
            name="deadline_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="technicianservicerequest",
            name="location_label",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AlterField(
            model_name="technicianservicerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("matching", "Matching"),
                    ("offers_received", "Offers Received"),
                    ("assigned", "Assigned"),
                    ("in_progress", "In Progress"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="open",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="TechnicianServiceOffer",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("proposed_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("message", models.TextField(blank=True)),
                ("estimated_hours", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("withdrawn", "Withdrawn"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offers",
                        to="marketplace_technicians.technicianservicerequest",
                    ),
                ),
                (
                    "technician_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offers",
                        to="marketplace_technicians.technicianprofile",
                    ),
                ),
            ],
            options={
                "db_table": "marketplace_technician_service_offers",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="technicianserviceoffer",
            constraint=models.UniqueConstraint(
                fields=("service_request", "technician_profile"),
                name="uniq_marketplace_service_offer_per_technician",
            ),
        ),
        migrations.AddField(
            model_name="technicianassignment",
            name="service_offer",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assignment",
                to="marketplace_technicians.technicianserviceoffer",
            ),
        ),
    ]
