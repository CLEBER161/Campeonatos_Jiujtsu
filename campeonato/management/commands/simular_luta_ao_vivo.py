"""
Simula uma luta ao vivo no tatame escolhido, registrando ações aleatórias
e exibindo o placar no terminal a cada evento.

Uso:
    python manage.py simular_luta_ao_vivo
    python manage.py simular_luta_ao_vivo --tatame 2
    python manage.py simular_luta_ao_vivo --intervalo 4 --max-acoes 15
"""
import random
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from campeonato.models import AcaoLuta, Luta, Tatame, TipoAcao


class Command(BaseCommand):
    help = 'Simula uma luta ao vivo com pontuações aleatórias'

    def add_arguments(self, parser):
        parser.add_argument('--tatame', type=int, default=1, help='ID do tatame (padrão: 1)')
        parser.add_argument('--intervalo', type=float, default=3.0, help='Segundos entre ações (padrão: 3)')
        parser.add_argument('--max-acoes', type=int, default=20, help='Quantidade máxima de ações antes de encerrar (padrão: 20)')
        parser.add_argument('--sem-finalizacao', action='store_true', help='Não registrar finalizações (encerra por pontos)')

    def handle(self, *args, **options):
        tatame_pk = options['tatame']
        intervalo = options['intervalo']
        max_acoes = options['max_acoes']
        sem_finalizacao = options['sem_finalizacao']

        # --- buscar tatame ---
        try:
            tatame = Tatame.objects.get(pk=tatame_pk)
        except Tatame.DoesNotExist:
            tatames = list(Tatame.objects.values_list('pk', 'nome'))
            self.stderr.write(f'Tatame {tatame_pk} não encontrado. Disponíveis: {tatames}')
            return

        # --- encerrar qualquer luta "em_andamento" antiga no tatame (limpeza) ---
        em_andamento = Luta.objects.filter(tatame=tatame, status='em_andamento').first()
        if em_andamento:
            self.stdout.write(f'⚠  Encontrada luta já em andamento (pk={em_andamento.pk}). Usando ela.')
            luta = em_andamento
        else:
            # pegar próxima luta aguardando neste tatame
            luta = Luta.objects.filter(
                tatame=tatame, status='aguardando',
                atleta1__isnull=False, atleta2__isnull=False,
            ).order_by('rodada', 'ordem').first()

            if not luta:
                # tentar qualquer luta aguardando no DB e atribuir ao tatame
                luta = Luta.objects.filter(
                    status='aguardando',
                    atleta1__isnull=False, atleta2__isnull=False,
                ).order_by('rodada', 'ordem').first()
                if luta:
                    luta.tatame = tatame
                    luta.save()
                    self.stdout.write(f'  Luta pk={luta.pk} atribuída ao {tatame}.')

            if not luta:
                # Resetar uma luta finalizada para poder simular de novo
                luta = Luta.objects.filter(
                    tatame=tatame,
                    atleta1__isnull=False, atleta2__isnull=False,
                    status='finalizada',
                ).order_by('rodada', 'ordem').first()
                if not luta:
                    luta = Luta.objects.filter(
                        atleta1__isnull=False, atleta2__isnull=False,
                        status='finalizada',
                    ).order_by('rodada', 'ordem').first()
                if not luta:
                    self.stderr.write('Nenhuma luta disponível. Rode simular_campeonato primeiro.')
                    return
                self.stdout.write(f'  ↺ Resetando luta finalizada (pk={luta.pk}) para aguardando...')
                luta.status = 'aguardando'
                luta.tatame = tatame
                luta.vencedor = None
                luta.resultado = 'pendente'
                luta.finalizada_em = None
                luta.finalizada_por = None
                luta.pontos_atleta1 = 0
                luta.pontos_atleta2 = 0
                luta.vantagens_atleta1 = 0
                luta.vantagens_atleta2 = 0
                luta.penalizacoes_atleta1 = 0
                luta.penalizacoes_atleta2 = 0
                luta.save()
                luta.acoes.all().delete()

            # iniciar a luta
            luta.status = 'em_andamento'
            luta.iniciada_em = timezone.now()
            luta.save()

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(f'  {tatame}  —  LUTA INICIADA!')
        self.stdout.write(f'  {luta.atleta1.nome}  VS  {luta.atleta2.nome}')
        self.stdout.write(f'  Categoria: {luta.chave.categoria}')
        self.stdout.write('=' * 60)
        self.stdout.write('')
        self.stdout.write('  Abra estas URLs no navegador:')
        self.stdout.write(f'  Mesa do árbitro → http://127.0.0.1:8000/arbitro/tatame/{tatame.pk}/')
        self.stdout.write(f'  Telão            → http://127.0.0.1:8000/tatame/{tatame.pk}/placar/')
        self.stdout.write('')
        self.stdout.write(f'  Registrando ações a cada {intervalo}s... (Ctrl+C para parar)')
        self.stdout.write('-' * 60)

        # --- carregar ações disponíveis ---
        cats_disponiveis = ['pontos', 'pontos', 'pontos', 'vantagem', 'penalizacao']
        if not sem_finalizacao:
            # finalizações só aparecem perto do fim (após 60% das ações)
            cats_finalizacao = ['finalizacao']
        else:
            cats_finalizacao = []

        acoes_por_cat = {}
        for cat in ['pontos', 'vantagem', 'penalizacao', 'finalizacao']:
            lista = list(TipoAcao.objects.filter(categoria=cat, ativo=True))
            if lista:
                acoes_por_cat[cat] = lista

        if not acoes_por_cat.get('pontos'):
            self.stderr.write('Nenhuma ação cadastrada. Rode: python manage.py seed_acoes')
            return

        atletas = [luta.atleta1, luta.atleta2]

        def placar_str(l):
            return (
                f'  {l.atleta1.nome[:16]:16} {l.pontos_atleta1:2}pts '
                f'{l.vantagens_atleta1}van {l.penalizacoes_atleta1}pen'
                f'   |   '
                f'{l.pontos_atleta2:2}pts {l.vantagens_atleta2}van '
                f'{l.penalizacoes_atleta2}pen  {l.atleta2.nome[:16]:16}'
            )

        n = 0
        try:
            while n < max_acoes:
                time.sleep(intervalo)

                # recarregar para pegar estado atual
                luta.refresh_from_db()
                if luta.status != 'em_andamento':
                    self.stdout.write('\n  Luta encerrada (status mudou externamente).')
                    break

                # escolher categoria — finalizações só após 60% das ações
                progresso = n / max_acoes
                pool = cats_disponiveis[:]
                if progresso >= 0.6 and cats_finalizacao:
                    pool += cats_finalizacao  # 1 em 6 chance de finalização

                cat = random.choice(pool)

                if cat not in acoes_por_cat:
                    continue

                tipo = random.choice(acoes_por_cat[cat])
                atleta = random.choice(atletas)
                is_a1 = (atleta == luta.atleta1)

                # aplicar pontos diretamente no model
                if cat == 'pontos':
                    if is_a1:
                        luta.pontos_atleta1 = max(0, luta.pontos_atleta1 + tipo.pontos)
                    else:
                        luta.pontos_atleta2 = max(0, luta.pontos_atleta2 + tipo.pontos)

                elif cat == 'vantagem':
                    if is_a1:
                        luta.vantagens_atleta1 = max(0, luta.vantagens_atleta1 + 1)
                    else:
                        luta.vantagens_atleta2 = max(0, luta.vantagens_atleta2 + 1)

                elif cat == 'penalizacao':
                    if is_a1:
                        luta.penalizacoes_atleta1 = max(0, luta.penalizacoes_atleta1 + 1)
                        luta.vantagens_atleta2 = max(0, luta.vantagens_atleta2 + 1)
                    else:
                        luta.penalizacoes_atleta2 = max(0, luta.penalizacoes_atleta2 + 1)
                        luta.vantagens_atleta1 = max(0, luta.vantagens_atleta1 + 1)

                elif cat == 'finalizacao':
                    luta.status = 'finalizada'
                    luta.finalizada_em = timezone.now()
                    luta.vencedor = atleta
                    luta.resultado = 'finalizacao'
                    luta.finalizada_por = None
                    luta.save()

                    AcaoLuta.objects.create(
                        luta=luta, atleta=atleta, tipo_acao=tipo,
                    )

                    self.stdout.write('')
                    self.stdout.write(f'  🔴 FINALIZAÇÃO! {atleta.nome} vence por {tipo.nome}!')
                    self.stdout.write(placar_str(luta))
                    self.stdout.write('')
                    self.stdout.write('  Luta encerrada.')
                    return

                luta.save()

                AcaoLuta.objects.create(
                    luta=luta, atleta=atleta, tipo_acao=tipo,
                )

                n += 1
                emoji = {'pontos': '🏅', 'vantagem': '⭐', 'penalizacao': '⚠'}.get(cat, '•')
                self.stdout.write(
                    f'  #{n:02}  {emoji} {atleta.nome[:18]:18}  {tipo.nome[:30]:30}  '
                    f'| Placar: {luta.pontos_atleta1}-{luta.pontos_atleta2}'
                )

        except KeyboardInterrupt:
            pass

        # Encerrar por pontos ao atingir max_acoes
        luta.refresh_from_db()
        if luta.status == 'em_andamento':
            # decidir vencedor por pontos
            if luta.pontos_atleta1 > luta.pontos_atleta2:
                vencedor = luta.atleta1
            elif luta.pontos_atleta2 > luta.pontos_atleta1:
                vencedor = luta.atleta2
            elif luta.vantagens_atleta1 > luta.vantagens_atleta2:
                vencedor = luta.atleta1
            elif luta.vantagens_atleta2 > luta.vantagens_atleta1:
                vencedor = luta.atleta2
            elif luta.penalizacoes_atleta1 < luta.penalizacoes_atleta2:
                vencedor = luta.atleta1
            elif luta.penalizacoes_atleta2 < luta.penalizacoes_atleta1:
                vencedor = luta.atleta2
            else:
                vencedor = random.choice([luta.atleta1, luta.atleta2])

            luta.status = 'finalizada'
            luta.finalizada_em = timezone.now()
            luta.vencedor = vencedor
            luta.resultado = 'pontos'
            luta.save()

            self.stdout.write('')
            self.stdout.write('-' * 60)
            self.stdout.write(f'  🏆 LUTA ENCERRADA — Vencedor por pontos: {vencedor.nome}')
        else:
            self.stdout.write('')

        luta.refresh_from_db()
        self.stdout.write(placar_str(luta))
        self.stdout.write('=' * 60)
