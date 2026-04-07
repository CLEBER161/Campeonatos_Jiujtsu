from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove a constraint que limitava 1 pessoa por tatame por campeonato.
    Agora cada tatame pode ter UM mesário E UM árbitro vinculados simultaneamente.
    """

    dependencies = [
        ('campeonato', '0010_campeonato_quantidade_tatames'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='arbitrotatame',
            name='unique_tatame_por_campeonato_no_arbitro',
        ),
    ]
