import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationBatch",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("batch_name", models.CharField(max_length=160)),
                (
                    "batch_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("campaign", "Campaign"),
                            ("system", "System"),
                            ("mass", "Mass"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("processing", "Processing"),
                            ("sent", "Sent"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notification_batches", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationChannel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                (
                    "channel_type",
                    models.CharField(
                        choices=[
                            ("in_app", "In App"),
                            ("email", "Email"),
                            ("sms", "SMS"),
                            ("whatsapp", "WhatsApp"),
                            ("webhook", "Webhook"),
                        ],
                        default="in_app",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notification_channels", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="NotificationEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_key", models.CharField(db_index=True, max_length=120)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("entity_type", models.CharField(blank=True, max_length=80)),
                ("entity_id", models.CharField(blank=True, max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notification_events", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="InAppNotification",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField()),
                ("link_url", models.CharField(blank=True, max_length=255)),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("success", "Success"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("action_required", "Action Required"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("unread", "Unread"), ("read", "Read"), ("archived", "Archived")],
                        default="unread",
                        max_length=20,
                    ),
                ),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="in_app_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "notification_in_app_notifications", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationMessage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_key", models.CharField(db_index=True, max_length=120)),
                ("recipient_address", models.CharField(blank=True, max_length=255)),
                ("subject_rendered", models.CharField(blank=True, max_length=255)),
                ("body_rendered", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("scheduled", "Scheduled"),
                            ("sent", "Sent"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("scheduled_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="notification_center.notificationchannel",
                    ),
                ),
                (
                    "recipient_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notification_messages",
                        to="companies.company",
                    ),
                ),
                (
                    "recipient_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notification_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "notification_messages", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("template_key", models.CharField(max_length=120, unique=True)),
                ("subject_template", models.CharField(blank=True, max_length=255)),
                ("body_template", models.TextField()),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="templates",
                        to="notification_center.notificationchannel",
                    ),
                ),
            ],
            options={"db_table": "notification_templates", "ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="messages",
                to="notification_center.notificationtemplate",
            ),
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_key", models.CharField(db_index=True, max_length=120)),
                ("is_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferences",
                        to="notification_center.notificationchannel",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preferences",
                        to="companies.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "notification_preferences", "ordering": ["event_key", "channel__name"]},
        ),
        migrations.CreateModel(
            name="NotificationDeliveryLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("provider_name", models.CharField(blank=True, max_length=80)),
                ("provider_reference", models.CharField(blank=True, max_length=120)),
                (
                    "delivery_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                            ("bounced", "Bounced"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="delivery_logs",
                        to="notification_center.notificationchannel",
                    ),
                ),
                (
                    "notification_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery_logs",
                        to="notification_center.notificationmessage",
                    ),
                ),
            ],
            options={"db_table": "notification_delivery_logs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NotificationBatchItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="notification_center.notificationbatch",
                    ),
                ),
                (
                    "notification_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="batch_items",
                        to="notification_center.notificationmessage",
                    ),
                ),
            ],
            options={"db_table": "notification_batch_items", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="notificationpreference",
            constraint=models.UniqueConstraint(fields=("user", "event_key", "channel"), name="uniq_user_event_channel_preference"),
        ),
        migrations.AddConstraint(
            model_name="notificationpreference",
            constraint=models.UniqueConstraint(fields=("company", "event_key", "channel"), name="uniq_company_event_channel_preference"),
        ),
        migrations.AddConstraint(
            model_name="notificationbatchitem",
            constraint=models.UniqueConstraint(fields=("batch", "notification_message"), name="uniq_notification_batch_message"),
        ),
    ]

