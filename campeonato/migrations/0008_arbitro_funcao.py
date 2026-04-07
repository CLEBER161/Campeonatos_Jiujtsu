from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campeonato', '0007_tipos_e_acoes_luta'),
    ]

    operations = [
        migrations.AddField(
            model_name='arbitro',
            name='funcao',
            field=models.CharField(
                choices=[('mesario', 'Mesário'), ('arbitro', 'Árbitro')],
                default='mesario',
                max_length=20,
            ),
        ),
    ]
