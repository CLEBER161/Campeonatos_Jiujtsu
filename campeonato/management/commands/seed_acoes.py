"""
Comando: python manage.py seed_acoes

Popula o banco com o catálogo completo de ações/posições do jiu-jitsu,
agrupadas por categoria (pontos, vantagem, penalização, finalização).

Pode ser rodado múltiplas vezes com segurança (usa get_or_create).
Use --limpar para remover e recriar tudo.
"""

from django.core.management.base import BaseCommand
from campeonato.models import TipoAcao


# ── Catálogo completo ─────────────────────────────────────────────────────────
# Formato: (nome, categoria, pontos, descrição, ordem)

ACOES = [
    # ── PONTOS ────────────────────────────────────────────────────────────────
    # 2 pontos
    ('Derrubada (Takedown)',        'pontos', 2, 'Projeção do adversário ao solo saindo em posição dominante.', 10),
    ('Raspagem (Sweep)',            'pontos', 2, 'Inversão de posição saindo por cima da guarda.', 11),
    ('Raspagem — Meia Guarda',     'pontos', 2, 'Raspagem executada a partir da meia guarda.', 12),
    ('Raspagem — Guarda Aranha',   'pontos', 2, 'Raspagem executada a partir da guarda aranha.', 13),
    ('Raspagem — De La Riva',      'pontos', 2, 'Raspagem executada a partir da guarda De La Riva.', 14),
    ('Raspagem — Tesoura',         'pontos', 2, 'Raspagem em tesoura (scissor sweep).', 15),
    ('Raspagem — Lasso',           'pontos', 2, 'Raspagem executada a partir da guarda lasso.', 16),
    ('Raspagem — X-Guard',         'pontos', 2, 'Raspagem executada a partir da guarda X.', 17),
    ('Projeção — Seoi Nage',       'pontos', 2, 'Projeção estilo judô com saída dominante.', 18),
    ('Projeção — Osoto Gari',      'pontos', 2, 'Projeção grande externa, saída dominante.', 19),
    ('Retorno ao solo (De pé)',     'pontos', 2, 'Derrubada a partir de posição em pé.', 20),

    # 3 pontos
    ('Passagem de Guarda',         'pontos', 3, 'Passagem completa da guarda, estabilizando o lado.', 30),
    ('Passagem de Guarda — Torreando', 'pontos', 3, 'Passagem torreando ao redor das pernas.', 31),
    ('Passagem de Guarda — Pressão', 'pontos', 3, 'Passagem de guarda com pressão ao solo.', 32),
    ('Passagem de Guarda — Leg Drag', 'pontos', 3, 'Passagem arrastando a perna.', 33),

    # 4 pontos
    ('Monte',                      'pontos', 4, 'Posição de monte estabilizada por 3 segundos.', 40),
    ('Monte Traseiro (Back Mount)', 'pontos', 4, 'Pegada nas costas com os dois ganchos.', 41),
    ('Joelho na Barriga',          'pontos', 4, 'Posição joelho na barriga estabilizada.', 42),
    ('Costas (Back Take)',         'pontos', 4, 'Pegada nas costas com controle dos ganchos.', 43),
    ('Costas — Da Guarda',        'pontos', 4, 'Pegada nas costas a partir de posição de guarda.', 44),

    # ── VANTAGEM ──────────────────────────────────────────────────────────────
    ('Tentativa de Finalização',   'vantagem', 1, 'Tentativa clara de finalização sem êxito.', 50),
    ('Raspagem Incompleta',        'vantagem', 1, 'Quase raspagem, adversário usando força para não cair.', 51),
    ('Passagem de Guarda Incompleta', 'vantagem', 1, 'Quase passagem de guarda, sem estabilizar.', 52),
    ('Derrubada Incompleta',       'vantagem', 1, 'Tentativa de derrubada que não completa.', 53),
    ('Joelho na Barriga Incompleto', 'vantagem', 1, 'Quase joelho na barriga, sem estabilizar 3s.', 54),
    ('Monte Incompleto',           'vantagem', 1, 'Quase monte, sem estabilizar os 3 segundos.', 55),
    ('Pressão Dominante',          'vantagem', 1, 'Posição dominante clara sem pontuação completa.', 56),

    # ── PENALIZAÇÃO ───────────────────────────────────────────────────────────
    ('Fuga de Faixa / Tapete',     'penalizacao', 0, 'Atleta saiu da área de luta intencionalmente.', 60),
    ('Passividade',                'penalizacao', 0, 'Falta de tentativa de luta / passividade.', 61),
    ('Falsa Guarda',               'penalizacao', 0, 'Sentar sem intenção de guardar.', 62),
    ('Guarda Sem Intenção',        'penalizacao', 0, 'Permanecer na guarda sem tentar finalizar ou vantagem.', 63),
    ('Segurar Calça / Manga',      'penalizacao', 0, 'Agarrar calça ou manga de forma ilegal.', 64),
    ('Empurrar Para Fora',         'penalizacao', 0, 'Empurrar adversário para fora do tatame.', 65),
    ('Posição Ilegal',             'penalizacao', 0, 'Uso de posição ou técnica ilegal.', 66),
    ('Advertência',                'penalizacao', 0, 'Advertência geral do árbitro.', 67),
    ('Falta Grave',                'penalizacao', 0, 'Falta grave que implica em penalização dupla.', 68),

    # ── FINALIZAÇÕES ──────────────────────────────────────────────────────────
    # Estrangulamentos
    ('Triângulo (Triangle Choke)',         'finalizacao', 0, 'Estrangulamento triangular com as pernas.', 70),
    ('Triângulo de Braço (Arm Triangle)',  'finalizacao', 0, 'Estrangulamento triangular usando o braço.', 71),
    ('Rear Naked Choke (Mata Leão)',       'finalizacao', 0, 'Estrangulamento pelas costas.', 72),
    ('Guillotine',                         'finalizacao', 0, 'Estrangulamento guilhotina pela frente.', 73),
    ('Guillotine — Arm In',               'finalizacao', 0, 'Guilhotina com o braço dentro.', 74),
    ('North-South Choke',                  'finalizacao', 0, 'Estrangulamento norte-sul.', 75),
    ('Estrangulamento de Lapela',          'finalizacao', 0, 'Estrangulamento usando a lapela do kimono.', 76),
    ('Ezekiel Choke (Katagatame)',         'finalizacao', 0, 'Estrangulamento com o braço dentro da manga.', 77),
    ('D\'Arce Choke',                      'finalizacao', 0, 'Variação do braço triangular.', 78),
    ('Anaconda',                           'finalizacao', 0, 'Estrangulamento anaconda (variação do D\'Arce).', 79),
    ('Baseball Bat Choke',                 'finalizacao', 0, 'Estrangulamento de lapela cruzado.', 80),
    ('Loop Choke',                         'finalizacao', 0, 'Estrangulamento de loop pela lapela.', 81),

    # Chaves de braço
    ('Kimura',                    'finalizacao', 0, 'Chave de ombro com pegada em 4.', 82),
    ('Americana (Ude Garami)',    'finalizacao', 0, 'Chave de ombro americana.', 83),
    ('Armlock (Juji Gatame)',     'finalizacao', 0, 'Chave de cotovelo (americana estendida).', 84),
    ('Straight Armlock',         'finalizacao', 0, 'Pressão direta no cotovelo.', 85),
    ('Omoplata',                 'finalizacao', 0, 'Chave de ombro com as pernas.', 86),
    ('Gogoplata',                'finalizacao', 0, 'Chave ou estrangulamento com a canela.', 87),
    ('Wristlock',                'finalizacao', 0, 'Chave de punho.', 88),

    # Chaves de perna
    ('Chave de Joelho (Kneebar)',      'finalizacao', 0, 'Pressão no joelho do adversário.', 90),
    ('Chave de Calcanhar (Heel Hook)', 'finalizacao', 0, 'Torção do joelho via calcanhar.', 91),
    ('Heel Hook Interno',              'finalizacao', 0, 'Heel hook pelo lado de dentro (mais perigoso).', 92),
    ('Heel Hook Externo',              'finalizacao', 0, 'Heel hook pelo lado de fora.', 93),
    ('Estrangulamento de Aquiles',     'finalizacao', 0, 'Pressão de tornozelo / achilles lock.', 94),
    ('Calf Slicer (Calf Crush)',       'finalizacao', 0, 'Compressão da panturrilha.', 95),
    ('Toe Hold',                       'finalizacao', 0, 'Torção do pé.', 96),
    ('Estrangulamento de Perna (Leg Lock)', 'finalizacao', 0, 'Chave de perna genérica.', 97),
]


class Command(BaseCommand):
    help = 'Popula o banco com o catálogo de ações do jiu-jitsu (TipoAcao)'

    def add_arguments(self, parser):
        parser.add_argument('--limpar', action='store_true', help='Remove todos os TipoAcao antes de recriar')

    def handle(self, *args, **options):
        if options['limpar']:
            total = TipoAcao.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'{total} ações removidas.'))

        criados = 0
        atualizados = 0
        for nome, categoria, pontos, descricao, ordem in ACOES:
            obj, created = TipoAcao.objects.update_or_create(
                nome=nome,
                defaults={
                    'categoria': categoria,
                    'pontos': pontos,
                    'descricao': descricao,
                    'ordem': ordem,
                    'ativo': True,
                },
            )
            if created:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✔ Catálogo de ações atualizado: {criados} criados, {atualizados} atualizados.'
        ))
        self._imprimir_resumo()

    def _imprimir_resumo(self):
        from campeonato.models import CATEGORIA_ACAO_CHOICES
        self.stdout.write('')
        for cat_key, cat_label in CATEGORIA_ACAO_CHOICES:
            count = TipoAcao.objects.filter(categoria=cat_key, ativo=True).count()
            self.stdout.write(f'  {cat_label:15s}: {count} ações')
        self.stdout.write(f'  {"TOTAL":15s}: {TipoAcao.objects.filter(ativo=True).count()}')
        self.stdout.write('')
