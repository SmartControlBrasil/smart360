import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0002_alter_user_managers_alter_user_groups_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180, verbose_name="título")),
                ("image", models.ImageField(upload_to="media_library/images/%Y/%m/", verbose_name="imagem")),
                ("alt_text", models.CharField(blank=True, max_length=255, verbose_name="texto alternativo")),
                ("file_size", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("mime_type", models.CharField(blank=True, editable=False, max_length=100)),
                ("width", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("height", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("is_active", models.BooleanField(default=True, verbose_name="ativa")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="media_library_assets",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="enviado por",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "imagem na biblioteca",
                "verbose_name_plural": "imagens na biblioteca",
            },
        ),
    ]
