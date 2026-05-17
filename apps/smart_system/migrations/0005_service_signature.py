from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0004_client_portal_request"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceSignature",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("signature_type", models.CharField(choices=[("technician_completion", "Technician Completion"), ("client_acceptance", "Client Acceptance"), ("supervisor_validation", "Supervisor Validation"), ("report_acknowledgement", "Report Acknowledgement")], max_length=40)),
                ("signer_role", models.CharField(choices=[("technician", "Technician"), ("client_responsible", "Client Responsible"), ("unit_representative", "Unit Representative"), ("supervisor", "Supervisor"), ("manager", "Manager")], max_length=40)),
                ("signer_name", models.CharField(max_length=180)),
                ("signer_title", models.CharField(blank=True, max_length=120)),
                ("signer_document", models.CharField(blank=True, max_length=60)),
                ("report_type", models.CharField(blank=True, max_length=60)),
                ("report_reference_code", models.CharField(blank=True, max_length=120)),
                ("checklist_execution_reference", models.CharField(blank=True, max_length=120)),
                ("signed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("signature_data", models.TextField(blank=True)),
                ("signature_format", models.CharField(default="data_url", max_length=30)),
                ("acceptance_notes", models.TextField(blank=True)),
                ("missing_reason", models.CharField(blank=True, choices=[("client_absent", "Client Absent"), ("responsible_unavailable", "Responsible Unavailable"), ("remote_service", "Remote Service"), ("signature_refused", "Signature Refused"), ("site_closed", "Site Closed"), ("other", "Other")], max_length=40)),
                ("missing_reason_notes", models.TextField(blank=True)),
                ("signed_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("device_info", models.CharField(blank=True, max_length=255)),
                ("request_id", models.CharField(blank=True, max_length=80)),
                ("correlation_id", models.CharField(blank=True, max_length=80)),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_current", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_signatures", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_signatures", to="smart_system.operationalsite")),
                ("service_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="service_signatures", to="smart_system.serviceorder")),
                ("signer_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_signatures", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "smart_system_service_signatures",
                "ordering": ["-signed_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="servicesignature",
            index=models.Index(fields=["signature_type", "is_current"], name="smart_signature_type_current_idx"),
        ),
        migrations.AddIndex(
            model_name="servicesignature",
            index=models.Index(fields=["service_order", "signature_type"], name="smart_signature_order_type_idx"),
        ),
    ]
