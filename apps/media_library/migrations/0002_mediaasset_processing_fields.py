from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("media_library", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="mediaasset",
            old_name="image",
            new_name="original_file",
        ),
        migrations.AlterField(
            model_name="mediaasset",
            name="original_file",
            field=models.ImageField(
                upload_to="media_library/images/%Y/%m/",
                verbose_name="arquivo original",
            ),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="asset_type",
            field=models.CharField(
                choices=[("IMAGE", "Imagem")],
                default="IMAGE",
                max_length=20,
                verbose_name="tipo de arquivo",
            ),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="processed_file",
            field=models.ImageField(
                blank=True,
                editable=False,
                null=True,
                upload_to="media_library/processed/%Y/%m/",
                verbose_name="arquivo tratado",
            ),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="processing_notes",
            field=models.TextField(blank=True, verbose_name="observações do processamento"),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="processing_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pendente"),
                    ("PROCESSING", "Processando"),
                    ("DONE", "Concluído"),
                    ("FAILED", "Falhou"),
                ],
                default="PENDING",
                max_length=20,
                verbose_name="status do processamento",
            ),
        ),
    ]
