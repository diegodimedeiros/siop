from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siop", "0004_contato_estado_contato_provincia"),
    ]

    operations = [
        migrations.AddField(
            model_name="contato",
            name="bairro",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Bairro",
            ),
        ),
    ]
