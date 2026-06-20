from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace_ecom", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="technicalproduct",
            name="display_order",
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                help_text="Ordem de exibição no catálogo (menor aparece primeiro).",
                verbose_name="ordem de exibição",
            ),
        ),
        migrations.AlterModelOptions(
            name="technicalproduct",
            options={
                "ordering": ("display_order", "-is_featured", "-updated_at"),
                "verbose_name": "produto técnico",
                "verbose_name_plural": "produtos técnicos do catálogo",
            },
        ),
    ]
