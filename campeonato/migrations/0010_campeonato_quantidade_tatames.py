from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campeonato', '0009_arbitro_senha_acesso'),
    ]

    operations = [
        migrations.AddField(
            model_name='campeonato',
            name='quantidade_tatames',
            field=models.PositiveIntegerField(default=4),
        ),
    ]
