from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siop", "0005_contato_bairro"),
    ]

    operations = [
        migrations.AddField(
            model_name="controleatendimento",
            name="recusa_atendimento",
            field=models.BooleanField(default=False, verbose_name="Recusa de Atendimento?"),
        ),
    ]
