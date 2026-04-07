from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campeonato', '0008_arbitro_funcao'),
    ]

    operations = [
        migrations.AddField(
            model_name='arbitro',
            name='senha_acesso',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
