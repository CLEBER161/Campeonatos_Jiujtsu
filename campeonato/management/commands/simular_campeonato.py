"""
Comando: python manage.py simular_campeonato

Popula o banco com dados fictícios completos:
- 1 Campeonato
- Categorias (faixa branca e azul, masculino e feminino)
- Baias e Tatames
- Árbitros (usuários Django)
- Atletas com inscrições e check-in
- Chaveamento e lutas simuladas com resultados
"""

import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from campeonato.models import (
    Campeonato, Categoria, Baia, Tatame, Arbitro, ArbitroTatame,
    Atleta, InscricaoCampeonato, CheckIn, Chave, Luta,
)


ACADEMIAS = [
    'GF Team', 'Alliance', 'Gracie Barra', 'Nova União', 'Atos',
    'Checkmat', 'Ribeiro JJ', 'BTT', 'Dream Art', 'Soul Fighters',
]

NOMES_M = [
    'Lucas', 'Gabriel', 'Rafael', 'Matheus', 'Felipe', 'Thiago',
    'Bruno', 'Diego', 'André', 'Pedro', 'Carlos', 'Henrique',
    'João', 'Gustavo', 'Rodrigo', 'Vinícius', 'Leandro', 'Eduardo',
    'Marcelo', 'Paulo', 'Fernando', 'Daniel', 'Caio', 'Igor',
]

NOMES_F = [
    'Ana', 'Beatriz', 'Camila', 'Daniela', 'Fernanda', 'Gabriela',
    'Helena', 'Isabela', 'Juliana', 'Larissa', 'Mariana', 'Natalia',
    'Patrícia', 'Rafaela', 'Sabrina', 'Thaís', 'Vanessa', 'Yasmin',
]

SOBRENOMES = [
    'Silva', 'Santos', 'Oliveira', 'Souza', 'Lima', 'Ferreira',
    'Costa', 'Carvalho', 'Almeida', 'Rodrigues', 'Nascimento', 'Gomes',
]


def nome_aleatorio(sexo):
    nomes = NOMES_M if sexo == 'M' else NOMES_F
    return f'{random.choice(nomes)} {random.choice(SOBRENOMES)}'


def data_nascimento_por_idade(idade_min, idade_max):
    if idade_min is None:
        idade_min = 18
    if idade_max is None:
        idade_max = 35
    idade = random.randint(idade_min, idade_max)
    hoje = date.today()
    return hoje.replace(year=hoje.year - idade) - timedelta(days=random.randint(0, 180))


class Command(BaseCommand):
    help = 'Popula o banco com uma simulação completa de campeonato de jiu-jitsu'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Apaga todos os dados existentes antes de simular',
        )

    def handle(self, *args, **options):
        if options['limpar']:
            self.stdout.write(self.style.WARNING('Apagando dados anteriores...'))
            Luta.objects.all().delete()
            Chave.objects.all().delete()
            CheckIn.objects.all().delete()
            InscricaoCampeonato.objects.all().delete()
            Atleta.objects.all().delete()
            ArbitroTatame.objects.all().delete()
            Arbitro.objects.all().delete()
            Tatame.objects.all().delete()
            Baia.objects.all().delete()
            Categoria.objects.all().delete()
            Campeonato.objects.all().delete()
            # Remove usuários de árbitros e atletas (não o superuser)
            User.objects.filter(is_superuser=False).delete()

        # ── 1. CAMPEONATO ─────────────────────────────────────────────────
        self.stdout.write('Criando campeonato...')
        campeonato = Campeonato.objects.create(
            nome='Campeonato Simulado de Jiu-Jitsu 2026',
            local='Ginásio Municipal — São Paulo/SP',
            data_evento=date(2026, 5, 10),
            inscricoes_abertas=True,
            ativo=True,
        )

        # ── 2. CATEGORIAS ─────────────────────────────────────────────────
        self.stdout.write('Criando categorias...')
        specs_categorias = [
            # (nome, faixa, sexo, peso_min, peso_max, idade_min, idade_max)
            ('Branca Masculino Leve',     'branca', 'M', 70.01, 76.00, 18, 29),
            ('Branca Masculino Médio',    'branca', 'M', 76.01, 82.30, 18, 29),
            ('Branca Masculino Pesado',   'branca', 'M', 88.31, 94.30, 18, 29),
            ('Branca Feminino Leve',      'branca', 'F', 58.51, 64.00, 18, 29),
            ('Azul Masculino Leve',       'azul',   'M', 70.01, 76.00, 18, 29),
            ('Azul Masculino Médio',      'azul',   'M', 76.01, 82.30, 18, 29),
            ('Azul Feminino Médio',       'azul',   'F', 64.01, 69.00, 18, 29),
            ('Roxa Masculino Pesado',     'roxa',   'M', 88.31, 94.30, 18, 35),
        ]
        categorias = []
        for nome, faixa, sexo, pmin, pmax, imin, imax in specs_categorias:
            cat = Categoria.objects.create(
                campeonato=campeonato,
                nome=nome,
                faixa=faixa,
                sexo=sexo,
                peso_min=pmin,
                peso_max=pmax,
                idade_min=imin,
                idade_max=imax,
            )
            categorias.append(cat)

        # ── 3. BAIAS ──────────────────────────────────────────────────────
        self.stdout.write('Criando baias...')
        baias = []
        for i in range(1, 5):
            b = Baia.objects.create(campeonato=campeonato, nome=f'Baia {i}', numero=i)
            baias.append(b)

        # ── 4. TATAMES ────────────────────────────────────────────────────
        self.stdout.write('Criando tatames...')
        tatames = []
        for i in range(1, 5):
            t = Tatame.objects.create(campeonato=campeonato, nome=f'Tatame {i}', numero=i)
            tatames.append(t)

        # ── 5. EQUIPE DE MESA E ÁRBITROS ─────────────────────────────────
        self.stdout.write('Criando equipe de mesa e árbitros...')
        arbitros = []
        mesarios = []
        for i in range(1, 5):
            username = f'mesario{i}'
            user, _ = User.objects.get_or_create(username=username)
            user.set_password('senha123')
            user.first_name = f'Mesário {i}'
            user.save()
            arb, _ = Arbitro.objects.get_or_create(
                usuario=user,
                defaults={'nome': f'Mesário {i}', 'funcao': Arbitro.FUNCAO_MESARIO},
            )
            arb.nome = f'Mesário {i}'
            arb.funcao = Arbitro.FUNCAO_MESARIO
            arb.senha_acesso = 'senha123'
            arb.ativo = True
            arb.save(update_fields=['nome', 'funcao', 'senha_acesso', 'ativo'])
            ArbitroTatame.objects.get_or_create(arbitro=arb, campeonato=campeonato, tatame=tatames[i - 1])
            mesarios.append(arb)

        for i in range(1, 5):
            username = f'arbitro{i}'
            user, _ = User.objects.get_or_create(username=username)
            user.set_password('senha123')
            user.first_name = f'Árbitro {i}'
            user.save()
            arb, _ = Arbitro.objects.get_or_create(
                usuario=user,
                defaults={'nome': f'Árbitro {i}', 'funcao': Arbitro.FUNCAO_ARBITRO},
            )
            arb.nome = f'Árbitro {i}'
            arb.funcao = Arbitro.FUNCAO_ARBITRO
            arb.senha_acesso = 'senha123'
            arb.ativo = True
            arb.save(update_fields=['nome', 'funcao', 'senha_acesso', 'ativo'])
            ArbitroTatame.objects.get_or_create(arbitro=arb, campeonato=campeonato, tatame=tatames[i - 1])
            arbitros.append(arb)

        # ── 6. ATLETAS E INSCRIÇÕES ───────────────────────────────────────
        self.stdout.write('Criando atletas...')
        # Distribuir atletas: 4-6 por categoria
        todos_atletas_por_cat = {}
        atleta_counter = 1

        for cat in categorias:
            quantidade = random.randint(4, 6)
            atletas_cat = []
            for _ in range(quantidade):
                nome = nome_aleatorio(cat.sexo)
                peso = round(random.uniform(float(cat.peso_min or cat.peso_max - 5), float(cat.peso_max or cat.peso_min + 5)), 2)
                dn = data_nascimento_por_idade(cat.idade_min, cat.idade_max)

                username = f'atleta{atleta_counter}'
                atleta_counter += 1
                user, _ = User.objects.get_or_create(username=username)
                user.set_password('senha123')
                user.save()

                # Usa QuerySet.update() pós-insert para evitar que o save()
                # automático dispare gerar_qr_code() e trave o comando.
                import uuid as _uuid
                codigo = _uuid.uuid4()
                atleta = Atleta(
                    usuario=user,
                    nome=nome,
                    data_nascimento=dn,
                    sexo=cat.sexo,
                    faixa=cat.faixa,
                    peso=peso,
                    academia=random.choice(ACADEMIAS),
                    categoria=cat,
                    codigo=codigo,
                )
                # Chama super().save() diretamente para pular o override
                super(Atleta, atleta).save()
                atletas_cat.append(atleta)

                # Inscrição com comprovante fictício (campo vazio mas aprovada manualmente)
                insc = InscricaoCampeonato.objects.create(
                    atleta=atleta,
                    campeonato=campeonato,
                    categoria=cat,
                    modalidade_inscricao='regular',
                )

                # Check-in em baia aleatória
                CheckIn.objects.create(
                    atleta=atleta,
                    inscricao=insc,
                    baia=random.choice(baias),
                    validado_por='Simulação',
                )

            todos_atletas_por_cat[cat.pk] = atletas_cat

        # ── 7. CHAVEAMENTO E LUTAS ────────────────────────────────────────
        self.stdout.write('Gerando chaveamento e lutas...')
        for idx, cat in enumerate(categorias):
            atletas = todos_atletas_por_cat[cat.pk]
            random.shuffle(atletas)

            tatame = tatames[idx % len(tatames)]
            baia = baias[idx % len(baias)]
            arbitro = arbitros[idx % len(arbitros)]

            chave = Chave.objects.create(
                categoria=cat,
                nome='Chave Principal',
                baia=baia,
                tatame=tatame,
            )

            # Rodada 1: pareamentos
            pares = []
            lista = atletas[:]
            # Se número ímpar: último recebe BYE
            if len(lista) % 2 != 0:
                bye_atleta = lista.pop()
            else:
                bye_atleta = None

            for i in range(0, len(lista), 2):
                pares.append((lista[i], lista[i + 1]))

            vencedores_r1 = []
            for ordem, (a1, a2) in enumerate(pares, start=1):
                vencedor, resultado_tipo = self._simular_resultado(a1, a2)
                luta = self._criar_luta(chave, a1, a2, vencedor, resultado_tipo, rodada=1, ordem=ordem, tatame=tatame, baia=baia, arbitro=arbitro)
                vencedores_r1.append(vencedor)

            if bye_atleta:
                vencedores_r1.append(bye_atleta)
                self._criar_luta(chave, bye_atleta, None, bye_atleta, 'bye', rodada=1, ordem=len(pares) + 1, tatame=tatame, baia=baia, arbitro=arbitro)

            # Rodada 2 (semifinal) se houver >= 2 vencedores
            vencedores_r2 = []
            if len(vencedores_r1) >= 2:
                random.shuffle(vencedores_r1)
                pares2 = []
                lista2 = vencedores_r1[:]
                bye2 = None
                if len(lista2) % 2 != 0:
                    bye2 = lista2.pop()
                for i in range(0, len(lista2), 2):
                    pares2.append((lista2[i], lista2[i + 1]))
                for ordem, (a1, a2) in enumerate(pares2, start=1):
                    vencedor, resultado_tipo = self._simular_resultado(a1, a2)
                    self._criar_luta(chave, a1, a2, vencedor, resultado_tipo, rodada=2, ordem=ordem, tatame=tatame, baia=baia, arbitro=arbitro)
                    vencedores_r2.append(vencedor)
                if bye2:
                    vencedores_r2.append(bye2)
                    self._criar_luta(chave, bye2, None, bye2, 'bye', rodada=2, ordem=len(pares2) + 1, tatame=tatame, baia=baia, arbitro=arbitro)

            # Final (rodada 3)
            if len(vencedores_r2) >= 2:
                a1, a2 = vencedores_r2[0], vencedores_r2[1]
                vencedor, resultado_tipo = self._simular_resultado(a1, a2)
                self._criar_luta(chave, a1, a2, vencedor, resultado_tipo, rodada=3, ordem=1, tatame=tatame, baia=baia, arbitro=arbitro)

        self.stdout.write(self.style.SUCCESS('\n✔ Simulação concluída com sucesso!'))
        self._imprimir_resumo(campeonato)

    def _simular_resultado(self, a1, a2):
        tipos = ['pontos', 'pontos', 'pontos', 'finalizacao', 'finalizacao', 'desclassificacao']
        resultado = random.choice(tipos)
        vencedor = random.choice([a1, a2])
        return vencedor, resultado

    def _criar_luta(self, chave, a1, a2, vencedor, resultado_tipo, rodada, ordem, tatame, baia, arbitro):
        from django.utils import timezone

        p1 = random.randint(0, 12) if resultado_tipo == 'pontos' else 0
        p2 = random.randint(0, p1) if resultado_tipo == 'pontos' else 0
        # Garante que o vencedor tem mais pontos (em caso de pontos)
        if resultado_tipo == 'pontos' and a2 and vencedor == a2:
            p1, p2 = p2, p1

        luta = Luta.objects.create(
            chave=chave,
            baia=baia,
            tatame=tatame,
            arbitro=arbitro,
            iniciada_por=arbitro,
            finalizada_por=arbitro,
            atleta1=a1,
            atleta2=a2,
            vencedor=vencedor,
            resultado=resultado_tipo,
            status='finalizada',
            pontos_atleta1=p1,
            pontos_atleta2=p2,
            vantagens_atleta1=random.randint(0, 3),
            vantagens_atleta2=random.randint(0, 3),
            penalizacoes_atleta1=random.randint(0, 2),
            penalizacoes_atleta2=random.randint(0, 2),
            rodada=rodada,
            ordem=ordem,
            iniciada_em=timezone.now() - timedelta(minutes=random.randint(10, 120)),
            realizada_em=timezone.now() - timedelta(minutes=random.randint(1, 9)),
        )
        return luta

    def _imprimir_resumo(self, campeonato):
        total_atletas = Atleta.objects.count()
        total_lutas = Luta.objects.count()
        total_cats = Categoria.objects.filter(campeonato=campeonato).count()
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════'))
        self.stdout.write(self.style.HTTP_INFO(f'  CAMPEONATO: {campeonato.nome}'))
        self.stdout.write(self.style.HTTP_INFO(f'  Categorias : {total_cats}'))
        self.stdout.write(self.style.HTTP_INFO(f'  Atletas    : {total_atletas}'))
        self.stdout.write(self.style.HTTP_INFO(f'  Lutas      : {total_lutas}'))
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════'))
        self.stdout.write('')
        self.stdout.write('  Acesso ao sistema:')
        self.stdout.write('  → Mesários : mesario1 / senha123  (até mesario4)')
        self.stdout.write('  → Árbitros : arbitro1 / senha123  (até arbitro4)')
        self.stdout.write('  → Atletas  : atleta1  / senha123  (numerados)')
        self.stdout.write('  → Admin    : crie um superuser com createsuperuser')
        self.stdout.write('')
