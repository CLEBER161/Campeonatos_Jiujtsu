from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Atleta, Categoria, Chave, Luta, Baia, CheckIn, Tatame, Campeonato, InscricaoCampeonato, Arbitro, ArbitroTatame, TipoAcao, AcaoLuta
from .forms import AtletaForm, CategoriaForm, LutaResultadoForm, CheckInForm, BaiaForm, TatameForm, CampeonatoForm, CadastroAtletaForm, InscricaoCampeonatoForm, CadastroArbitroForm, ArbitroTatameForm
from .default_categories import get_category_parameter_options, seed_default_categories, RULE_PRESETS
from datetime import date
import math
import secrets
import string


# ---------------------------------------------------------------------------
# Decorator: Organização
# ---------------------------------------------------------------------------

def organizacao_required(view_func):
    """Exige que o usuário seja staff/superusuário para acessar uma view de organização."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Faça login para acessar a área da organização.')
            return redirect('organizacao_login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'Seu usuário não tem permissão para acessar a área da organização.')
            return redirect('organizacao_login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_campeonato_atual(request, obrigatorio=False):
    campeonato_id = request.GET.get('campeonato') or request.session.get('campeonato_atual_id')
    campeonato = None

    if campeonato_id:
        campeonato = Campeonato.objects.filter(pk=campeonato_id).first()

    if not campeonato:
        campeonato = Campeonato.objects.filter(ativo=True).order_by('-data_evento', '-criado_em').first()

    if not campeonato:
        campeonato = Campeonato.objects.order_by('-data_evento', '-criado_em').first()

    if campeonato:
        request.session['campeonato_atual_id'] = campeonato.pk
    elif obrigatorio:
        messages.warning(request, 'Crie ou selecione um campeonato primeiro.')

    return campeonato


def get_inscricao_atual(atleta, campeonato=None, campeonato_id=None):
    inscricoes = atleta.inscricoes.select_related('categoria', 'campeonato').order_by('-criado_em')
    if campeonato_id:
        inscricao = inscricoes.filter(campeonato_id=campeonato_id).first()
        if inscricao:
            return inscricao
    if campeonato:
        inscricao = inscricoes.filter(campeonato=campeonato).first()
        if inscricao:
            return inscricao
    return inscricoes.first()


def redirecionar_origem(request, fallback):
    destino = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(destino or fallback)


def gerar_senha_automatica(tamanho=8):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


def get_perfil_equipe_atual(request):
    if not request.user.is_authenticated:
        return None
    return Arbitro.objects.filter(usuario=request.user, ativo=True).first()


def get_arbitro_atual(request):
    if not request.user.is_authenticated:
        return None
    return Arbitro.objects.filter(usuario=request.user, ativo=True, funcao=Arbitro.FUNCAO_ARBITRO).first()


def get_mesario_atual(request):
    if not request.user.is_authenticated:
        return None
    return Arbitro.objects.filter(usuario=request.user, ativo=True, funcao=Arbitro.FUNCAO_MESARIO).first()


def nome_home_equipe(perfil):
    if perfil and perfil.funcao == Arbitro.FUNCAO_MESARIO:
        return 'mesario_home'
    return 'arbitro_home'


def usuario_pode_operar_tatame(request, tatame):
    if request.user.is_staff or request.user.is_superuser:
        return True
    arbitro = get_perfil_equipe_atual(request)
    if not arbitro:
        return False
    return ArbitroTatame.objects.filter(
        arbitro=arbitro,
        campeonato=tatame.campeonato,
        tatame=tatame,
    ).exists()


def montar_ranking(categoria=None, campeonato=None):
    """Monta ranking por vitorias e pontos marcados."""
    inscricoes_qs = InscricaoCampeonato.objects.select_related('atleta', 'categoria', 'campeonato')
    if categoria:
        inscricoes_qs = inscricoes_qs.filter(categoria=categoria)
        campeonato = categoria.campeonato
    elif campeonato:
        inscricoes_qs = inscricoes_qs.filter(campeonato=campeonato)

    ranking = []
    for inscricao in inscricoes_qs:
        atleta = inscricao.atleta
        lutas = Luta.objects.filter(
            Q(atleta1=atleta) | Q(atleta2=atleta),
            chave__categoria__campeonato=campeonato,
        ).exclude(resultado='pendente')

        vitorias = lutas.filter(vencedor=atleta).count()
        derrotas = lutas.filter(vencedor__isnull=False).exclude(vencedor=atleta).count()

        pontos_pro = 0
        pontos_contra = 0
        for luta in lutas:
            if luta.atleta1_id == atleta.id:
                pontos_pro += luta.pontos_atleta1
                pontos_contra += luta.pontos_atleta2
            elif luta.atleta2_id == atleta.id:
                pontos_pro += luta.pontos_atleta2
                pontos_contra += luta.pontos_atleta1

        saldo = pontos_pro - pontos_contra
        ranking.append({
            'atleta': atleta,
            'inscricao': inscricao,
            'vitorias': vitorias,
            'derrotas': derrotas,
            'pontos_pro': pontos_pro,
            'pontos_contra': pontos_contra,
            'saldo': saldo,
        })

    ranking.sort(
        key=lambda item: (
            item['vitorias'],
            item['saldo'],
            item['pontos_pro'],
            -item['derrotas'],
            item['atleta'].nome.lower(),
        ),
        reverse=True,
    )

    for posicao, item in enumerate(ranking, start=1):
        item['posicao'] = posicao

    return ranking


def atualizar_chaveamento_categoria(categoria):
    """Atualiza automaticamente a chave de uma categoria conforme as inscricoes."""
    if not categoria:
        return {'status': 'sem-categoria'}

    chave_existente = Chave.objects.filter(categoria=categoria).order_by('-criada_em').first()
    lutas_bloqueadas = Luta.objects.filter(
        chave__categoria=categoria,
        status__in=['em_andamento', 'finalizada'],
    ).exists()

    if lutas_bloqueadas:
        return {'status': 'bloqueada', 'chave': chave_existente}

    inscricoes = list(categoria.inscricoes.select_related('atleta').order_by('criado_em', 'id'))
    atletas = [inscricao.atleta for inscricao in inscricoes]
    total_atletas = len(atletas)

    if total_atletas < 2:
        Chave.objects.filter(categoria=categoria).delete()
        return {'status': 'insuficiente'}

    baia_padrao = chave_existente.baia if chave_existente else None
    tatame_padrao = chave_existente.tatame if chave_existente else None
    tatames_disponiveis = list(Tatame.objects.filter(campeonato=categoria.campeonato, ativo=True).order_by('numero'))
    if tatames_disponiveis and not tatame_padrao:
        tatame_padrao = tatames_disponiveis[0]
    Chave.objects.filter(categoria=categoria).delete()

    chave = Chave.objects.create(
        categoria=categoria,
        nome='Chave Principal',
        baia=baia_padrao,
        tatame=tatame_padrao,
    )

    potencia = 2 ** math.ceil(math.log2(total_atletas)) if total_atletas > 1 else 2
    byes = potencia - total_atletas
    atletas_com_bye = atletas + [None] * byes

    for i in range(0, len(atletas_com_bye), 2):
        atleta1 = atletas_com_bye[i]
        atleta2 = atletas_com_bye[i + 1]
        resultado = 'bye' if atleta2 is None else 'pendente'
        vencedor = atleta1 if atleta2 is None else None
        tatame_luta = tatame_padrao
        if tatames_disponiveis:
            tatame_luta = tatames_disponiveis[(i // 2) % len(tatames_disponiveis)]
        Luta.objects.create(
            chave=chave,
            baia=baia_padrao,
            tatame=tatame_luta,
            atleta1=atleta1,
            atleta2=atleta2,
            rodada=1,
            ordem=(i // 2) + 1,
            resultado=resultado,
            vencedor=vencedor,
        )

    return {'status': 'gerada', 'chave': chave, 'total_atletas': total_atletas}


def encontrar_categoria_por_dados(faixa, sexo, peso, idade):
    """Encontra automaticamente a categoria por faixa, sexo, peso e idade."""
    return encontrar_categoria_por_dados_no_campeonato(None, faixa, sexo, peso, idade)


def encontrar_categoria_por_dados_no_campeonato(campeonato, faixa, sexo, peso, idade):
    """Encontra automaticamente a categoria por faixa, sexo, peso e idade em um campeonato."""
    categorias = Categoria.objects.filter(
        campeonato=campeonato,
        faixa=faixa,
        sexo=sexo,
    ).order_by('idade_min', 'peso_min', 'nome')

    categorias_lista = list(categorias)
    if not categorias_lista:
        return None

    for categoria in categorias_lista:
        idade_valida = True
        peso_valido = True

        if categoria.idade_min is not None and idade < categoria.idade_min:
            idade_valida = False
        if categoria.idade_max is not None and idade > categoria.idade_max:
            idade_valida = False

        if categoria.peso_min is not None and peso < categoria.peso_min:
            peso_valido = False
        if categoria.peso_max is not None and peso > categoria.peso_max:
            peso_valido = False

        if idade_valida and peso_valido:
            return categoria

    # Fallback: escolhe a categoria mais próxima para evitar atleta sem categoria
    # quando existe categoria na mesma faixa/sexo, mas os limites não batem exatamente.
    def distancia_faixa(valor, minimo, maximo):
        if minimo is not None and valor < minimo:
            return float(minimo - valor)
        if maximo is not None and valor > maximo:
            return float(valor - maximo)
        return 0.0

    def idade_esta_no_intervalo(categoria):
        if categoria.idade_min is not None and idade < categoria.idade_min:
            return False
        if categoria.idade_max is not None and idade > categoria.idade_max:
            return False
        return True

    candidatas_idade = [c for c in categorias_lista if idade_esta_no_intervalo(c)]
    base_candidatas = candidatas_idade if candidatas_idade else categorias_lista

    categoria_proxima = min(
        base_candidatas,
        key=lambda c: (
            distancia_faixa(peso, c.peso_min, c.peso_max),
            distancia_faixa(idade, c.idade_min, c.idade_max),
            c.id,
        ),
    )
    return categoria_proxima

    return None


def encontrar_categoria_para_atleta(atleta):
    """Encontra automaticamente a categoria do atleta por faixa, sexo, peso e idade."""
    campeonato = getattr(atleta, 'campeonato_atual', None)
    return encontrar_categoria_por_dados_no_campeonato(
        campeonato=campeonato,
        faixa=atleta.faixa,
        sexo=atleta.sexo,
        peso=atleta.peso,
        idade=atleta.idade,
    )


def atleta_prever_categoria(request):
    """Retorna a categoria provável do atleta antes de salvar o cadastro."""
    campeonato = get_campeonato_atual(request)
    if not campeonato:
        return JsonResponse({'ok': False, 'mensagem': 'Nenhum campeonato ativo selecionado.'})

    data_nascimento = request.GET.get('data_nascimento')
    sexo = request.GET.get('sexo')
    faixa = request.GET.get('faixa')
    peso = request.GET.get('peso')

    if not all([data_nascimento, sexo, faixa, peso]):
        return JsonResponse({'ok': False, 'mensagem': 'Preencha data, sexo, faixa e peso.'})

    try:
        nascimento = date.fromisoformat(data_nascimento)
        hoje = date.today()
        idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        peso_valor = float(peso)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos para prever categoria.'})

    categoria = encontrar_categoria_por_dados_no_campeonato(
        campeonato=campeonato,
        faixa=faixa,
        sexo=sexo,
        peso=peso_valor,
        idade=idade,
    )

    if not categoria:
        return JsonResponse({'ok': False, 'mensagem': 'Nenhuma categoria compatível encontrada.'})

    return JsonResponse({
        'ok': True,
        'categoria': str(categoria),
        'categoria_nome': categoria.nome,
    })


# ===================== HOME =====================
def home(request):
    campeonato = get_campeonato_atual(request)
    total_atletas = InscricaoCampeonato.objects.filter(campeonato=campeonato).count() if campeonato else 0
    total_categorias = Categoria.objects.filter(campeonato=campeonato).count() if campeonato else 0
    total_lutas = Luta.objects.filter(chave__categoria__campeonato=campeonato).count() if campeonato else 0
    lutas_pendentes = Luta.objects.filter(chave__categoria__campeonato=campeonato, resultado='pendente').count() if campeonato else 0
    context = {
        'campeonato_atual': campeonato,
        'campeonatos_abertos': Campeonato.objects.filter(inscricoes_abertas=True).order_by('data_evento', 'nome')[:6],
        'total_atletas': total_atletas,
        'total_categorias': total_categorias,
        'total_lutas': total_lutas,
        'lutas_pendentes': lutas_pendentes,
    }
    return render(request, 'campeonato/home.html', context)


def atleta_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_atleta'):
            return redirect('minha_area_atleta')
        if hasattr(request.user, 'perfil_arbitro'):
            perfil = request.user.perfil_arbitro
            messages.info(request, f'Você está logado como {perfil.get_funcao_display().lower()}. Faça logout para entrar com outra conta de atleta.')
            return redirect(nome_home_equipe(perfil))
        messages.info(request, 'Você já está logado. Faça logout para entrar com outra conta de atleta.')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('minha_area_atleta')
        messages.error(request, 'Usuario ou senha invalidos.')

    return render(request, 'campeonato/atleta_login.html')


def atleta_cadastro(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_atleta'):
            messages.info(request, 'Você já está logado com uma conta de atleta.')
            return redirect('minha_area_atleta')
        if hasattr(request.user, 'perfil_arbitro'):
            perfil = request.user.perfil_arbitro
            messages.warning(request, f'Você está logado como {perfil.get_funcao_display().lower()}. Faça logout para criar outra conta de atleta.')
            return redirect(nome_home_equipe(perfil))
        messages.warning(request, 'Faça logout antes de criar uma nova conta de atleta.')
        return redirect('home')

    form = CadastroAtletaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        user = form.save()
        atleta_existente = Atleta.objects.filter(
            nome__iexact=form.cleaned_data['nome'].strip(),
            data_nascimento=form.cleaned_data['data_nascimento'],
            academia__iexact=form.cleaned_data['academia'].strip(),
        ).order_by('id').first()

        if atleta_existente and atleta_existente.usuario_id:
            user.delete()
            messages.error(request, 'Já existe uma conta vinculada para este atleta. Fale com a organização para recuperação de acesso.')
            return render(request, 'campeonato/atleta_cadastro.html', {'form': form})

        if atleta_existente:
            atleta = atleta_existente
            atleta.usuario = user
            atleta.sexo = form.cleaned_data['sexo']
            atleta.faixa = form.cleaned_data['faixa']
            atleta.peso = form.cleaned_data['peso']
            if form.cleaned_data.get('foto'):
                atleta.foto = form.cleaned_data.get('foto')
            atleta.save()
        else:
            atleta = Atleta.objects.create(
                usuario=user,
                nome=form.cleaned_data['nome'],
                data_nascimento=form.cleaned_data['data_nascimento'],
                sexo=form.cleaned_data['sexo'],
                faixa=form.cleaned_data['faixa'],
                peso=form.cleaned_data['peso'],
                academia=form.cleaned_data['academia'],
                foto=form.cleaned_data.get('foto'),
            )
        login(request, user)
        messages.success(request, f'Conta criada com sucesso para {atleta.nome}.')
        return redirect('minha_area_atleta')

    return render(request, 'campeonato/atleta_cadastro.html', {'form': form})


def atleta_logout(request):
    logout(request)
    messages.success(request, 'Sessao encerrada com sucesso.')
    return redirect('atleta_login')


@login_required
def minha_area_atleta(request):
    atleta = Atleta.objects.filter(usuario=request.user).first()
    if not atleta:
        if hasattr(request.user, 'perfil_arbitro'):
            perfil = request.user.perfil_arbitro
            messages.info(request, f'Este usuário é de {perfil.get_funcao_display().lower()}. Use a área da equipe para continuar.')
            return redirect(nome_home_equipe(perfil))
        messages.error(request, 'Seu usuario nao esta vinculado a um atleta. Fale com a organizacao.')
        return redirect('home')

    campeonato_id = request.GET.get('campeonato')
    inscricao = get_inscricao_atual(atleta, campeonato_id=campeonato_id)
    campeonato = inscricao.campeonato if inscricao else None

    lutas = Luta.objects.filter(
        Q(atleta1=atleta) | Q(atleta2=atleta),
        chave__categoria__campeonato=campeonato,
    ).select_related('atleta1', 'atleta2', 'vencedor', 'chave').order_by('rodada', 'ordem')

    chave = Chave.objects.filter(categoria=inscricao.categoria).order_by('-criada_em').first() if inscricao and inscricao.categoria else None

    ranking_geral = montar_ranking(campeonato=campeonato) if campeonato else []
    ranking_categoria = montar_ranking(inscricao.categoria) if inscricao and inscricao.categoria else []
    minha_geral = next((item for item in ranking_geral if item['atleta'].id == atleta.id), None)
    minha_categoria = next((item for item in ranking_categoria if item['atleta'].id == atleta.id), None)

    return render(request, 'campeonato/minha_area_atleta.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'inscricao_form': InscricaoCampeonatoForm(instance=inscricao) if inscricao else None,
        'campeonato_atual': campeonato,
        'minhas_inscricoes': atleta.inscricoes.select_related('campeonato', 'categoria').order_by('-criado_em'),
        'campeonatos_abertos': Campeonato.objects.filter(inscricoes_abertas=True).exclude(inscricoes__atleta=atleta).order_by('data_evento', 'nome'),
        'lutas': lutas[:8],
        'chave': chave,
        'minha_geral': minha_geral,
        'minha_categoria': minha_categoria,
    })


@login_required
def atleta_tatames_tempo_real(request):
    """Painel para atleta acompanhar as mesas de arbitro por tatame em tempo real."""
    atleta = Atleta.objects.filter(usuario=request.user).first()
    if not atleta:
        messages.error(request, 'Seu usuario nao esta vinculado a um atleta. Fale com a organizacao.')
        return redirect('home')

    inscricao = get_inscricao_atual(atleta, campeonato_id=request.GET.get('campeonato'))
    campeonato = inscricao.campeonato if inscricao else None

    luta_em_andamento_atleta = Luta.objects.filter(
        Q(atleta1=atleta) | Q(atleta2=atleta),
        chave__categoria__campeonato=campeonato,
        status='em_andamento',
    ).select_related('tatame', 'chave__categoria').order_by('rodada', 'ordem').first()

    proxima_luta_atleta = Luta.objects.filter(
        Q(atleta1=atleta) | Q(atleta2=atleta),
        chave__categoria__campeonato=campeonato,
        status='aguardando',
        resultado='pendente',
    ).select_related('tatame', 'chave__categoria').order_by('rodada', 'ordem', 'id').first()

    tatame_destaque_id = None
    if luta_em_andamento_atleta and luta_em_andamento_atleta.tatame_id:
        tatame_destaque_id = luta_em_andamento_atleta.tatame_id
    elif proxima_luta_atleta and proxima_luta_atleta.tatame_id:
        tatame_destaque_id = proxima_luta_atleta.tatame_id

    tatames = Tatame.objects.filter(campeonato=campeonato, ativo=True).order_by('numero')
    paineis = []
    for tatame in tatames:
        lutas_tatame = Luta.objects.filter(tatame=tatame).select_related(
            'atleta1', 'atleta2', 'vencedor', 'chave__categoria'
        )
        luta_atual = lutas_tatame.filter(status='em_andamento').order_by('rodada', 'ordem').first()
        proximas = lutas_tatame.filter(status='aguardando', resultado='pendente').order_by('rodada', 'ordem')[:3]
        finalizadas = lutas_tatame.filter(status='finalizada').order_by('-realizada_em', '-id')[:3]

        paineis.append({
            'tatame': tatame,
            'luta_atual': luta_atual,
            'proximas': proximas,
            'finalizadas': finalizadas,
            'is_destaque': tatame.id == tatame_destaque_id,
        })

    return render(request, 'campeonato/atleta_tatames_tempo_real.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'campeonato_atual': campeonato,
        'paineis': paineis,
        'luta_em_andamento_atleta': luta_em_andamento_atleta,
        'proxima_luta_atleta': proxima_luta_atleta,
        'tatame_destaque_id': tatame_destaque_id,
    })


# ===================== ESPACOS =====================
def espaco_atletas(request):
    """Portal para os atletas: inscricao e credenciais."""
    campeonato = get_campeonato_atual(request)
    total_atletas = InscricaoCampeonato.objects.filter(campeonato=campeonato).count() if campeonato else 0
    return render(request, 'campeonato/espaco_atletas.html', {
        'total_atletas': total_atletas,
        'campeonato_atual': campeonato,
        'campeonatos_disponiveis': Campeonato.objects.filter(inscricoes_abertas=True).order_by('data_evento', 'nome'),
    })


def organizacao_login(request):
    """Tela de login da organização (apenas staff/superusuários)."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('organizacao_home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect(request.POST.get('next') or 'organizacao_home')
        messages.error(request, 'Usuário ou senha inválidos, ou sem permissão de organização.')
    return render(request, 'campeonato/organizacao_login.html', {
        'next': request.GET.get('next', ''),
    })


def organizacao_logout(request):
    """Encerra a sessão da organização."""
    logout(request)
    messages.success(request, 'Sessão da organização encerrada.')
    return redirect('organizacao_login')


@organizacao_required
def organizacao_home(request):
    """Portal da organizacao: hub com seções administrativas."""
    campeonato = get_campeonato_atual(request)
    total_atletas = InscricaoCampeonato.objects.filter(campeonato=campeonato).count() if campeonato else 0
    total_categorias = Categoria.objects.filter(campeonato=campeonato).count() if campeonato else 0
    total_lutas = Luta.objects.filter(chave__categoria__campeonato=campeonato).count() if campeonato else 0
    lutas_finalizadas = Luta.objects.filter(chave__categoria__campeonato=campeonato, status='finalizada').count() if campeonato else 0
    checkins = CheckIn.objects.filter(inscricao__campeonato=campeonato).count() if campeonato else 0
    return render(request, 'campeonato/organizacao_home.html', {
        'campeonato_atual': campeonato,
        'total_atletas': total_atletas,
        'total_categorias': total_categorias,
        'total_lutas': total_lutas,
        'lutas_finalizadas': lutas_finalizadas,
        'checkins': checkins,
    })


@organizacao_required
def organizacao_campeonatos(request):
    campeonato = get_campeonato_atual(request)
    return render(request, 'campeonato/organizacao_campeonatos.html', {
        'campeonato_atual': campeonato,
        'campeonato_form': CampeonatoForm(),
        'campeonatos': Campeonato.objects.order_by('-data_evento', '-criado_em')[:20],
    })


@organizacao_required
def organizacao_categorias(request):
    campeonato = get_campeonato_atual(request)
    category_options = get_category_parameter_options()
    return render(request, 'campeonato/organizacao_categorias.html', {
        'campeonato_atual': campeonato,
        'rule_presets': category_options['rule_presets'],
        'belt_groups': category_options['belt_groups'],
        'sex_scopes': category_options['sex_scopes'],
        'total_categorias': Categoria.objects.filter(campeonato=campeonato).count() if campeonato else 0,
    })


@organizacao_required
def organizacao_estrutura(request):
    campeonato = get_campeonato_atual(request)
    baias = Baia.objects.filter(campeonato=campeonato).order_by('numero')[:30] if campeonato else []
    tatames = Tatame.objects.filter(campeonato=campeonato).order_by('numero')[:30] if campeonato else []
    vinculos = ArbitroTatame.objects.filter(campeonato=campeonato).select_related('arbitro', 'tatame') if campeonato else ArbitroTatame.objects.none()

    # Dict tatame_id → {mesario: vinculo|None, arbitro: vinculo|None}
    tatame_equipe_dict = {}
    for v in vinculos:
        tid = v.tatame_id
        if tid not in tatame_equipe_dict:
            tatame_equipe_dict[tid] = {'mesario': None, 'arbitro': None}
        if v.arbitro.funcao == Arbitro.FUNCAO_MESARIO:
            tatame_equipe_dict[tid]['mesario'] = v
        else:
            tatame_equipe_dict[tid]['arbitro'] = v

    return render(request, 'campeonato/organizacao_estrutura.html', {
        'campeonato_atual': campeonato,
        'baia_form': BaiaForm(),
        'tatame_form': TatameForm(campeonato=campeonato),
        'baias': baias,
        'tatames': tatames,
        'tatame_equipe_dict': tatame_equipe_dict,
    })


@organizacao_required
@require_POST
def organizacao_rebalancear_tatames(request):
    """Redistribui lutas pendentes priorizando menor fila e agrupando categorias por tatame."""
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_estrutura')

    escopo = request.POST.get('escopo', 'todas')
    if escopo not in {'rodada1', 'todas'}:
        escopo = 'todas'

    tatames = list(Tatame.objects.filter(campeonato=campeonato, ativo=True).order_by('numero'))
    if not tatames:
        messages.warning(request, 'Não há tatames ativos para rebalancear as lutas.')
        return redirecionar_origem(request, 'organizacao_estrutura')

    lutas_qs = Luta.objects.filter(
        chave__categoria__campeonato=campeonato,
        status='aguardando',
        resultado='pendente',
        atleta1__isnull=False,
        atleta2__isnull=False,
    )
    if escopo == 'rodada1':
        lutas_qs = lutas_qs.filter(rodada=1)

    lutas_pendentes = list(
        lutas_qs.filter(
            chave__categoria__campeonato=campeonato,
        )
        .select_related('chave__categoria')
        .order_by('rodada', 'ordem', 'id')
    )

    if not lutas_pendentes:
        if escopo == 'rodada1':
            messages.info(request, 'Nenhuma luta pendente da rodada 1 encontrada para rebalanceamento.')
        else:
            messages.info(request, 'Nenhuma luta pendente encontrada para rebalanceamento.')
        return redirecionar_origem(request, 'organizacao_estrutura')

    pendentes_ids = [l.pk for l in lutas_pendentes]

    # Carga base: lutas não finalizadas já fixadas no tatame (fora do lote rebalanceado).
    carga_tatame = {tatame.pk: 0 for tatame in tatames}
    cargas_existentes = (
        Luta.objects.filter(
            chave__categoria__campeonato=campeonato,
            tatame__in=tatames,
        )
        .exclude(status='finalizada')
        .exclude(pk__in=pendentes_ids)
        .values('tatame_id')
        .annotate(total=Count('id'))
    )
    for item in cargas_existentes:
        tatame_id = item['tatame_id']
        if tatame_id in carga_tatame:
            carga_tatame[tatame_id] = item['total']

    # Agrupa lutas pendentes por categoria para reduzir troca de atletas entre tatames.
    lutas_por_categoria = {}
    preferencia_categoria = {}
    for luta in lutas_pendentes:
        categoria_id = luta.chave.categoria_id
        lutas_por_categoria.setdefault(categoria_id, []).append(luta)
        if luta.tatame_id:
            pref = preferencia_categoria.setdefault(categoria_id, {})
            pref[luta.tatame_id] = pref.get(luta.tatame_id, 0) + 1

    categorias_ordenadas = sorted(
        lutas_por_categoria.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )

    alocacao_categoria_tatame = {}
    alteradas = 0
    for categoria_id, lutas_categoria in categorias_ordenadas:
        tatame_preferido = None
        pref = preferencia_categoria.get(categoria_id, {})
        if pref:
            tatame_preferido = max(pref.items(), key=lambda x: x[1])[0]

        # Escolhe o tatame com menor carga, priorizando manter a categoria no mesmo tatame quando possível.
        melhor_tatame = min(
            tatames,
            key=lambda tatame: (
                carga_tatame[tatame.pk],
                0 if tatame_preferido and tatame.pk == tatame_preferido else 1,
                tatame.numero,
            ),
        )

        alocacao_categoria_tatame[categoria_id] = melhor_tatame.pk

        for luta in sorted(lutas_categoria, key=lambda l: (l.rodada, l.ordem, l.id)):
            if luta.tatame_id != melhor_tatame.pk:
                luta.tatame = melhor_tatame
                luta.save(update_fields=['tatame'])
                alteradas += 1
            carga_tatame[melhor_tatame.pk] += 1

    categorias_mesmo_tatame = len(alocacao_categoria_tatame)

    messages.success(
        request,
        (
            f'Rebalanceamento concluído: {alteradas} luta(s) atualizada(s), '
            f'{categorias_mesmo_tatame} categoria(s) agrupada(s) por tatame, '
            f'priorizando menor fila entre {len(tatames)} tatame(s) ativos '
            f'({"apenas rodada 1" if escopo == "rodada1" else "todas as rodadas pendentes"}).'
        ),
    )
    return redirecionar_origem(request, 'organizacao_estrutura')


@organizacao_required
def organizacao_arbitros(request):
    campeonato = get_campeonato_atual(request)
    credenciais_mesarios = ArbitroTatame.objects.filter(
        campeonato=campeonato,
        arbitro__funcao=Arbitro.FUNCAO_MESARIO,
    ).select_related('arbitro', 'tatame').order_by('tatame__numero') if campeonato else ArbitroTatame.objects.none()

    vinculos_qs = ArbitroTatame.objects.filter(campeonato=campeonato).select_related('arbitro', 'tatame').order_by('tatame__numero') if campeonato else ArbitroTatame.objects.none()

    # Agrupar vínculos por tatame mostrando mesário e árbitro separados
    tatame_equipe = {}
    for v in vinculos_qs:
        tid = v.tatame_id
        if tid not in tatame_equipe:
            tatame_equipe[tid] = {'tatame': v.tatame, 'mesario': None, 'arbitro': None}
        if v.arbitro.funcao == Arbitro.FUNCAO_MESARIO:
            tatame_equipe[tid]['mesario'] = v
        else:
            tatame_equipe[tid]['arbitro'] = v

    return render(request, 'campeonato/organizacao_arbitros.html', {
        'campeonato_atual': campeonato,
        'arbitro_form': CadastroArbitroForm(),
        'funcoes_equipe': Arbitro.FUNCAO_CHOICES,
        'form_mesario': ArbitroTatameForm(campeonato=campeonato, funcao=Arbitro.FUNCAO_MESARIO),
        'form_arbitro': ArbitroTatameForm(campeonato=campeonato, funcao=Arbitro.FUNCAO_ARBITRO),
        'arbitros': Arbitro.objects.select_related('usuario').order_by('-ativo', 'nome')[:50],
        'tatame_equipe': list(tatame_equipe.values()),
        'credenciais_mesarios': credenciais_mesarios,
    })


@organizacao_required
@require_POST
def organizacao_criar_categorias_padrao(request):
    """Cria categorias padrão do campeonato conforme parâmetros selecionados."""
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_categorias')

    rule_preset = request.POST.get('rule_preset', 'cbjj_adulto')
    belt_group = request.POST.get('belt_group', 'todas')
    sex_scope = request.POST.get('sex_scope', 'ambos')
    clear_existing = request.POST.get('clear_existing') == 'on'

    try:
        result = seed_default_categories(
            campeonato=campeonato,
            rule_preset=rule_preset,
            belt_group=belt_group,
            sex_scope=sex_scope,
            clear_existing=clear_existing,
        )
    except ValueError:
        messages.error(request, 'Parâmetros inválidos para criação de categorias.')
        return redirect('organizacao_home')

    if result['created_count']:
        messages.success(
            request,
            (
                f"Categorias criadas: {result['created_count']} | "
                f"Perfil: {result['rule_label']} | "
                f"Faixas: {result['belt_label']} | "
                f"Sexo: {result['sex_label']}"
            ),
        )
    else:
        messages.info(request, 'Nenhuma categoria nova foi criada para os parâmetros escolhidos.')

    if result['deleted_count']:
        messages.warning(request, f"Categorias removidas antes da recriação: {result['deleted_count']}.")

    return redirecionar_origem(request, 'organizacao_categorias')


@organizacao_required
@require_POST
def organizacao_gerar_categorias_completas(request):
    """Gera todas as categorias padrão (juvenil, adulto, masters e no-gi) no campeonato atual."""
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_categorias')

    total_criadas = 0
    for rule_preset in RULE_PRESETS.keys():
        result = seed_default_categories(
            campeonato=campeonato,
            rule_preset=rule_preset,
            belt_group='todas',
            sex_scope='ambos',
            clear_existing=False,
        )
        total_criadas += result['created_count']

    if total_criadas:
        messages.success(request, f'Categorias completas geradas com sucesso. Novas categorias criadas: {total_criadas}.')
    else:
        messages.info(request, 'As categorias completas já estavam cadastradas para este campeonato.')

    return redirecionar_origem(request, 'organizacao_categorias')


@organizacao_required
@require_POST
def organizacao_criar_campeonato(request):
    form = CampeonatoForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            campeonato = form.save()

            # Cria a estrutura de tatames e usuários de mesa automaticamente
            total_tatames = max(1, campeonato.quantidade_tatames)
            for i in range(1, total_tatames + 1):
                tatame = Tatame.objects.create(
                    campeonato=campeonato,
                    nome=f'Tatame {i}',
                    numero=i,
                )

                username_base = f'mesario_c{campeonato.pk}_t{i}'
                username = username_base
                sufixo = 1
                while User.objects.filter(username=username).exists():
                    sufixo += 1
                    username = f'{username_base}_{sufixo}'

                senha_auto = gerar_senha_automatica(8)
                user = User.objects.create_user(
                    username=username,
                    email='',
                    password=senha_auto,
                )
                user.first_name = f'Mesário Tatame {i}'
                user.save(update_fields=['first_name'])

                mesario = Arbitro.objects.create(
                    usuario=user,
                    nome=f'Mesário Tatame {i}',
                    funcao=Arbitro.FUNCAO_MESARIO,
                    senha_acesso=senha_auto,
                    ativo=True,
                )

                ArbitroTatame.objects.create(
                    arbitro=mesario,
                    campeonato=campeonato,
                    tatame=tatame,
                )

        request.session['campeonato_atual_id'] = campeonato.pk
        messages.success(request, f'Campeonato criado com sucesso: {campeonato}. Estrutura inicial criada com {campeonato.quantidade_tatames} tatames e mesários automáticos.')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Dados inválidos.'
        messages.error(request, f'Não foi possível criar o campeonato. {erro}')
    return redirecionar_origem(request, 'organizacao_campeonatos')


@organizacao_required
@require_POST
def organizacao_selecionar_campeonato(request):
    campeonato = get_object_or_404(Campeonato, pk=request.POST.get('campeonato_id'))
    request.session['campeonato_atual_id'] = campeonato.pk
    messages.success(request, f'Campeonato atual selecionado: {campeonato}.')
    return redirecionar_origem(request, 'organizacao_campeonatos')


@organizacao_required
@require_POST
def organizacao_criar_baia(request):
    """Cria uma nova baia diretamente na area da organizacao."""
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_estrutura')

    form = BaiaForm(request.POST)
    if form.is_valid():
        baia = form.save(commit=False)
        baia.campeonato = campeonato
        baia.save()
        messages.success(request, f'Baia criada com sucesso: {baia}.')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Dados inválidos.'
        messages.error(request, f'Não foi possível criar a baia. {erro}')
    return redirecionar_origem(request, 'organizacao_estrutura')


@organizacao_required
@require_POST
def organizacao_criar_tatame(request):
    """Cria um novo tatame diretamente na area da organizacao."""
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_estrutura')

    form = TatameForm(request.POST, campeonato=campeonato)
    if form.is_valid():
        with transaction.atomic():
            arbitro = form.cleaned_data.get('arbitro_existente')
            if not arbitro:
                user = User.objects.create_user(
                    username=form.cleaned_data['arbitro_username'],
                    email=form.cleaned_data['arbitro_email'],
                    password=form.cleaned_data['arbitro_password1'],
                )
                arbitro = Arbitro.objects.create(
                    usuario=user,
                    nome=form.cleaned_data['arbitro_nome'],
                    funcao=Arbitro.FUNCAO_MESARIO,
                    senha_acesso=form.cleaned_data['arbitro_password1'],
                    ativo=True,
                )

            tatame = form.save(commit=False)
            tatame.campeonato = campeonato
            tatame.save()

            ArbitroTatame.objects.update_or_create(
                campeonato=campeonato,
                tatame=tatame,
                defaults={'arbitro': arbitro},
            )

        messages.success(request, f'Tatame criado com sucesso: {tatame}. Árbitro responsável: {arbitro.nome}.')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Dados inválidos.'
        messages.error(request, f'Não foi possível criar o tatame. {erro}')
    return redirecionar_origem(request, 'organizacao_estrutura')


@organizacao_required
@require_POST
def organizacao_criar_arbitro(request):
    dados = request.POST.copy()
    funcao = dados.get('funcao', Arbitro.FUNCAO_MESARIO)
    gerar_auto = dados.get('gerar_senha_automatica') == 'on'
    senha_gerada = ''
    if funcao == Arbitro.FUNCAO_MESARIO and gerar_auto:
        senha_gerada = gerar_senha_automatica()
        dados['password1'] = senha_gerada
        dados['password2'] = senha_gerada

    form = CadastroArbitroForm(dados)
    if form.is_valid():
        user = form.save()
        user.email = form.cleaned_data['email']
        user.save(update_fields=['email'])
        funcoes_validas = {valor for valor, _ in Arbitro.FUNCAO_CHOICES}
        if funcao not in funcoes_validas:
            funcao = Arbitro.FUNCAO_MESARIO
        senha_acesso = senha_gerada or form.cleaned_data['password1']
        arbitro = Arbitro.objects.create(
            usuario=user,
            nome=form.cleaned_data['nome'],
            funcao=funcao,
            senha_acesso=senha_acesso,
            ativo=True,
        )
        messages.success(request, f'{arbitro.get_funcao_display()} criado com sucesso: {arbitro.nome}.')
        if arbitro.funcao == Arbitro.FUNCAO_MESARIO:
            messages.info(request, f'Credencial do mesário: usuário {arbitro.usuario.username} | senha {arbitro.senha_acesso}')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Dados inválidos.'
        messages.error(request, f'Não foi possível criar o perfil da equipe. {erro}')
    return redirecionar_origem(request, 'organizacao_arbitros')


@organizacao_required
def organizacao_credenciais_mesarios(request):
    campeonato = get_campeonato_atual(request)
    credenciais = ArbitroTatame.objects.filter(
        campeonato=campeonato,
        arbitro__funcao=Arbitro.FUNCAO_MESARIO,
    ).select_related('arbitro', 'tatame').order_by('tatame__numero') if campeonato else ArbitroTatame.objects.none()

    return render(request, 'campeonato/organizacao_credenciais_mesarios.html', {
        'campeonato_atual': campeonato,
        'credenciais': credenciais,
    })


@organizacao_required
@require_POST
def organizacao_status_arbitro(request, pk):
    arbitro = get_object_or_404(Arbitro, pk=pk)
    acao = request.POST.get('acao')
    if acao == 'aprovar':
        arbitro.ativo = True
        arbitro.save(update_fields=['ativo'])
        messages.success(request, f'Árbitro aprovado: {arbitro.nome}.')
    elif acao == 'inativar':
        arbitro.ativo = False
        arbitro.save(update_fields=['ativo'])
        messages.warning(request, f'Árbitro inativado: {arbitro.nome}.')
    else:
        messages.error(request, 'Ação inválida para status do árbitro.')
    return redirecionar_origem(request, 'organizacao_arbitros')


@organizacao_required
@require_POST
def organizacao_vincular_arbitro_tatame(request):
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirecionar_origem(request, 'organizacao_arbitros')

    form = ArbitroTatameForm(request.POST, campeonato=campeonato)
    if form.is_valid():
        arbitro = form.cleaned_data['arbitro']
        tatame = form.cleaned_data['tatame']
        # Remove qualquer vínculo anterior da mesma função neste tatame
        ArbitroTatame.objects.filter(
            campeonato=campeonato,
            tatame=tatame,
            arbitro__funcao=arbitro.funcao,
        ).delete()
        ArbitroTatame.objects.create(campeonato=campeonato, tatame=tatame, arbitro=arbitro)
        messages.success(request, f'{arbitro.nome} ({arbitro.get_funcao_display()}) vinculado ao {tatame}.')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Dados inválidos.'
        messages.error(request, f'Não foi possível vincular ao tatame. {erro}')
    return redirecionar_origem(request, 'organizacao_arbitros')


@organizacao_required
@require_POST
def organizacao_remover_vinculo_arbitro(request, pk):
    vinculo = get_object_or_404(ArbitroTatame, pk=pk)
    messages.success(request, f'Vínculo removido: {vinculo.arbitro.nome} e {vinculo.tatame}.')
    vinculo.delete()
    return redirecionar_origem(request, 'organizacao_arbitros')


@login_required
def atleta_inscrever_campeonato(request, campeonato_pk):
    atleta = get_object_or_404(Atleta, usuario=request.user)
    campeonato = get_object_or_404(Campeonato, pk=campeonato_pk, inscricoes_abertas=True)
    inscricao, created = InscricaoCampeonato.objects.get_or_create(
        atleta=atleta,
        campeonato=campeonato,
    )

    if request.method == 'POST':
        form = InscricaoCampeonatoForm(request.POST, request.FILES, instance=inscricao)
        if form.is_valid():
            inscricao = form.save(commit=False)
            atleta.campeonato_atual = campeonato
            categoria = encontrar_categoria_para_atleta(atleta)
            if categoria:
                inscricao.categoria = categoria
            inscricao.save()
            if categoria:
                atualizar_chaveamento_categoria(categoria)
            messages.success(request, f'Inscrição atualizada com sucesso em {campeonato.nome}.')
            return redirect(f'/atleta/minha-area/?campeonato={campeonato.pk}')
    else:
        form = InscricaoCampeonatoForm(instance=inscricao)

    atleta.campeonato_atual = campeonato
    categoria = encontrar_categoria_para_atleta(atleta)
    if categoria and not inscricao.categoria:
        inscricao.categoria = categoria
        inscricao.save(update_fields=['categoria'])

    if created and request.method != 'POST':
        messages.info(request, 'Escolha a modalidade da inscrição e envie o documento necessário para liberar o QR Code.')

    return render(request, 'campeonato/atleta_inscricao_campeonato.html', {
        'atleta': atleta,
        'campeonato': campeonato,
        'inscricao': inscricao,
        'form': form,
    })


# ===================== ATLETAS =====================
def atleta_lista(request):
    campeonato = get_campeonato_atual(request)
    q = request.GET.get('q', '')
    atletas = Atleta.objects.all()
    if campeonato:
        atletas = atletas.filter(inscricoes__campeonato=campeonato).distinct()
    if q:
        atletas = atletas.filter(Q(nome__icontains=q) | Q(academia__icontains=q))
    atletas = atletas.order_by('nome')
    for atleta in atletas:
        atleta.inscricao_atual = get_inscricao_atual(atleta, campeonato=campeonato)
    return render(request, 'campeonato/atleta_lista.html', {'atletas': atletas, 'q': q})


def atleta_criar(request):
    campeonato = get_campeonato_atual(request)
    form = AtletaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        atleta = form.save(commit=False)
        atleta.save()
        atleta.campeonato_atual = campeonato
        categoria = encontrar_categoria_para_atleta(atleta) if campeonato else None
        atleta.categoria = categoria
        atleta.save(update_fields=['categoria'])
        if campeonato:
            inscricao, _ = InscricaoCampeonato.objects.get_or_create(atleta=atleta, campeonato=campeonato)
            inscricao.categoria = categoria
            inscricao.save()
            resultado_chave = atualizar_chaveamento_categoria(categoria)
        else:
            resultado_chave = {'status': 'sem-categoria'}

        if resultado_chave['status'] == 'gerada':
            messages.success(request, f'Atleta cadastrado com sucesso em {campeonato.nome} na categoria {categoria}. O chaveamento foi atualizado automaticamente.')
        elif resultado_chave['status'] == 'bloqueada':
            messages.warning(request, f'Atleta cadastrado com sucesso em {campeonato.nome} na categoria {categoria}, mas a chave não foi atualizada porque já existem lutas em andamento/finalizadas.')
        elif categoria:
            messages.success(request, f'Atleta cadastrado com sucesso na categoria {categoria}.')
        else:
            messages.warning(request, 'Atleta cadastrado, mas nenhuma categoria automática compatível foi encontrada para o campeonato atual.')
        return redirect('atleta_lista')
    return render(request, 'campeonato/atleta_form.html', {'form': form, 'titulo': 'Cadastrar Atleta'})


def atleta_editar(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    form = AtletaForm(request.POST or None, request.FILES or None, instance=atleta)
    if form.is_valid():
        inscricao = get_inscricao_atual(atleta, campeonato=campeonato)
        categoria_anterior = inscricao.categoria if inscricao else atleta.categoria
        atleta = form.save(commit=False)
        atleta.campeonato_atual = campeonato
        atleta.categoria = encontrar_categoria_para_atleta(atleta) if campeonato else None
        atleta.save()
        if campeonato:
            inscricao, _ = InscricaoCampeonato.objects.get_or_create(atleta=atleta, campeonato=campeonato)
            inscricao.categoria = atleta.categoria
            inscricao.save()
        atualizar_chaveamento_categoria(atleta.categoria)
        if categoria_anterior and categoria_anterior != atleta.categoria:
            atualizar_chaveamento_categoria(categoria_anterior)
        if atleta.categoria:
            messages.success(request, f'Atleta atualizado com sucesso. Categoria automática: {atleta.categoria}.')
        else:
            messages.warning(request, 'Atleta atualizado, mas nenhuma categoria automática compatível foi encontrada.')
        return redirect('atleta_lista')
    return render(request, 'campeonato/atleta_form.html', {'form': form, 'titulo': 'Editar Atleta', 'atleta': atleta})


def atleta_excluir(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    if request.method == 'POST':
        inscricao = get_inscricao_atual(atleta, campeonato=campeonato)
        categoria = inscricao.categoria if inscricao else atleta.categoria
        if inscricao:
            inscricao.delete()
            atualizar_chaveamento_categoria(categoria)
            messages.success(request, 'Inscrição do atleta removida com sucesso deste campeonato!')
        else:
            atleta.delete()
            messages.success(request, 'Atleta removido com sucesso!')
        return redirect('atleta_lista')
    return render(request, 'campeonato/confirmar_exclusao.html', {'objeto': atleta, 'tipo': 'Atleta'})


def atleta_detalhe(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    inscricao = get_inscricao_atual(atleta, campeonato=campeonato)
    lutas = Luta.objects.filter(
        Q(atleta1=atleta) | Q(atleta2=atleta),
        chave__categoria__campeonato=campeonato,
    ).select_related('atleta1', 'atleta2', 'vencedor')
    ranking_categoria = []
    minha_posicao = None
    if inscricao and inscricao.categoria:
        ranking_categoria = montar_ranking(inscricao.categoria)
        for item in ranking_categoria:
            if item['atleta'].id == atleta.id:
                minha_posicao = item['posicao']
                break

    return render(request, 'campeonato/atleta_detalhe.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'campeonato_atual': campeonato,
        'lutas': lutas,
        'minha_posicao': minha_posicao,
    })


def atleta_chaveamento(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    inscricao = get_inscricao_atual(atleta, campeonato=campeonato)
    if not inscricao or not inscricao.categoria:
        messages.warning(request, 'Este atleta ainda nao esta em uma categoria.')
        return redirect('atleta_detalhe', pk=atleta.pk)

    chave = Chave.objects.filter(categoria=inscricao.categoria).order_by('-criada_em').first()
    if not chave:
        messages.warning(request, 'Ainda nao ha chaveamento gerado para esta categoria.')
        return redirect('atleta_detalhe', pk=atleta.pk)

    lutas = chave.lutas.select_related('atleta1', 'atleta2', 'vencedor').order_by('rodada', 'ordem')
    rodadas = {}
    for luta in lutas:
        rodadas.setdefault(luta.rodada, []).append(luta)

    return render(request, 'campeonato/atleta_chaveamento.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'chave': chave,
        'rodadas': rodadas,
    })


def atleta_ranking(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    inscricao = get_inscricao_atual(atleta, campeonato=campeonato)

    ranking_geral = montar_ranking(campeonato=campeonato) if campeonato else []
    ranking_categoria = montar_ranking(inscricao.categoria) if inscricao and inscricao.categoria else []

    minha_geral = next((item for item in ranking_geral if item['atleta'].id == atleta.id), None)
    minha_categoria = next((item for item in ranking_categoria if item['atleta'].id == atleta.id), None)

    return render(request, 'campeonato/atleta_ranking.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'ranking_geral': ranking_geral[:20],
        'ranking_categoria': ranking_categoria[:20],
        'minha_geral': minha_geral,
        'minha_categoria': minha_categoria,
    })


# ===================== CATEGORIAS =====================
def categoria_lista(request):
    campeonato = get_campeonato_atual(request)
    categorias = Categoria.objects.filter(campeonato=campeonato).annotate(total_atletas=Count('inscricoes')) if campeonato else Categoria.objects.none()
    return render(request, 'campeonato/categoria_lista.html', {'categorias': categorias, 'campeonato_atual': campeonato})


def categoria_criar(request):
    campeonato = get_campeonato_atual(request, obrigatorio=True)
    if not campeonato:
        return redirect('organizacao_home')

    form = CategoriaForm(request.POST or None)
    if form.is_valid():
        categoria = form.save(commit=False)
        categoria.campeonato = campeonato
        categoria.save()
        messages.success(request, 'Categoria criada com sucesso!')
        return redirect('categoria_lista')
    return render(request, 'campeonato/categoria_form.html', {'form': form, 'titulo': 'Nova Categoria'})


def categoria_editar(request, pk):
    campeonato = get_campeonato_atual(request)
    categoria = get_object_or_404(Categoria, pk=pk, campeonato=campeonato)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if form.is_valid():
        form.save()
        messages.success(request, 'Categoria atualizada com sucesso!')
        return redirect('categoria_lista')
    return render(request, 'campeonato/categoria_form.html', {'form': form, 'titulo': 'Editar Categoria', 'categoria': categoria})


def categoria_excluir(request, pk):
    campeonato = get_campeonato_atual(request)
    categoria = get_object_or_404(Categoria, pk=pk, campeonato=campeonato)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria removida com sucesso!')
        return redirect('categoria_lista')
    return render(request, 'campeonato/confirmar_exclusao.html', {'objeto': categoria, 'tipo': 'Categoria'})


# ===================== CHAVES / BRACKET =====================
def chave_gerar(request, categoria_pk):
    categoria = get_object_or_404(Categoria, pk=categoria_pk)
    resultado = atualizar_chaveamento_categoria(categoria)

    if resultado['status'] == 'insuficiente':
        messages.warning(request, 'É necessário pelo menos 2 atletas na categoria para gerar a chave.')
        return redirect('categoria_lista')

    if resultado['status'] == 'bloqueada':
        messages.warning(request, 'A chave não pode ser regenerada porque já existem lutas em andamento ou finalizadas.')
        if resultado.get('chave'):
            return redirect('chave_detalhe', pk=resultado['chave'].pk)
        return redirect('categoria_lista')

    messages.success(request, f'Chave gerada com {resultado["total_atletas"]} atletas!')
    return redirect('chave_detalhe', pk=resultado['chave'].pk)


def chave_detalhe(request, pk):
    chave = get_object_or_404(Chave, pk=pk)
    lutas = chave.lutas.select_related('atleta1', 'atleta2', 'vencedor').order_by('rodada', 'ordem')
    rodadas = {}
    for luta in lutas:
        rodadas.setdefault(luta.rodada, []).append(luta)
    return render(request, 'campeonato/chave_detalhe.html', {'chave': chave, 'rodadas': rodadas})


@organizacao_required
def organizacao_tatames_chave(request, pk):
    """Tela da organizacao para distribuir lutas de uma chave entre baias e tatames."""
    chave = get_object_or_404(Chave, pk=pk)
    tatames = Tatame.objects.filter(campeonato=chave.categoria.campeonato, ativo=True).order_by('numero')
    baias = Baia.objects.filter(campeonato=chave.categoria.campeonato, ativa=True).order_by('numero')
    lutas = chave.lutas.select_related('atleta1', 'atleta2', 'tatame', 'baia').order_by('rodada', 'ordem')

    if request.method == 'POST':
        luta = get_object_or_404(Luta, pk=request.POST.get('luta_id'), chave=chave)
        tatame_pk = request.POST.get('tatame_pk')
        baia_pk = request.POST.get('baia_pk')

        if tatame_pk:
            luta.tatame = get_object_or_404(Tatame, pk=tatame_pk)
        else:
            luta.tatame = None

        if baia_pk:
            luta.baia = get_object_or_404(Baia, pk=baia_pk)
        else:
            luta.baia = None

        luta.save()
        messages.success(request, f'Localização da luta atualizada: {luta}.')
        return redirect('organizacao_tatames_chave', pk=chave.pk)

    return render(request, 'campeonato/organizacao_tatames_chave.html', {
        'chave': chave,
        'lutas': lutas,
        'tatames': tatames,
        'baias': baias,
    })


# ===================== LUTAS =====================
def luta_resultado(request, pk):
    luta = get_object_or_404(Luta, pk=pk)
    arbitro = get_perfil_equipe_atual(request)
    if request.user.is_authenticated and arbitro and luta.tatame and not usuario_pode_operar_tatame(request, luta.tatame):
        messages.error(request, 'Você não pode registrar resultado neste tatame.')
        return redirect(nome_home_equipe(arbitro))

    form = LutaResultadoForm(request.POST or None, instance=luta)
    if form.is_valid():
        luta_salva = form.save(commit=False)
        from django.utils import timezone
        luta_salva.realizada_em = timezone.now()
        luta_salva.status = 'finalizada'
        if arbitro:
            luta_salva.arbitro = arbitro
            luta_salva.finalizada_por = arbitro
        luta_salva.save()
        messages.success(request, 'Resultado registrado!')
        if arbitro and luta.tatame:
            return redirect('mesario_tatame', pk=luta.tatame.pk)
        return redirect('chave_detalhe', pk=luta.chave.pk)
    return render(request, 'campeonato/luta_resultado.html', {'form': form, 'luta': luta, 'arbitro': arbitro})


# ===================== CREDENCIAL / QR CODE =====================
def atleta_credencial(request, pk):
    campeonato = get_campeonato_atual(request)
    atleta = get_object_or_404(Atleta, pk=pk)
    inscricao = get_inscricao_atual(atleta, campeonato=campeonato)
    if not inscricao:
        messages.warning(request, 'Este atleta ainda não possui inscrição no campeonato selecionado.')
        return redirect('atleta_detalhe', pk=atleta.pk)
    if not inscricao.documentacao_ok:
        messages.warning(request, inscricao.pendencia_documental)
        return redirect(f'/atleta/campeonatos/{inscricao.campeonato.pk}/inscrever/')
    if not inscricao.qr_code:
        inscricao.gerar_qr_code(request.build_absolute_uri('/').rstrip('/'))
    return render(request, 'campeonato/atleta_credencial.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'campeonato_atual': campeonato,
        'ja_fez_checkin': hasattr(inscricao, 'checkin'),
    })


# ===================== PORTAL APOIO =====================
def apoio_home(request):
    """Portal do suporte: scanner de QR code e lista de check-ins."""
    campeonato = get_campeonato_atual(request)
    checkins = CheckIn.objects.filter(inscricao__campeonato=campeonato).select_related('atleta', 'inscricao__atleta', 'baia').order_by('-realizado_em')[:50] if campeonato else CheckIn.objects.none()
    baias = Baia.objects.filter(campeonato=campeonato, ativa=True) if campeonato else Baia.objects.none()
    total_checkins = CheckIn.objects.filter(inscricao__campeonato=campeonato).count() if campeonato else 0
    total_atletas = InscricaoCampeonato.objects.filter(campeonato=campeonato).count() if campeonato else 0
    return render(request, 'campeonato/apoio_home.html', {
        'campeonato_atual': campeonato,
        'checkins': checkins,
        'baias': baias,
        'total_checkins': total_checkins,
        'total_atletas': total_atletas,
    })


def apoio_inscricoes(request):
    """Lista todos os atletas inscritos com status de pagamento e pesagem."""
    campeonato = get_campeonato_atual(request)
    if not campeonato:
        messages.warning(request, 'Selecione um campeonato primeiro.')
        return redirect('apoio_home')

    filtro = request.GET.get('filtro', 'todos')
    inscricoes_qs = InscricaoCampeonato.objects.filter(
        campeonato=campeonato,
    ).select_related('atleta', 'categoria').order_by('atleta__nome')

    if filtro == 'sem_pagamento':
        inscricoes_qs = inscricoes_qs.filter(pagamento_confirmado=False)
    elif filtro == 'sem_pesagem':
        inscricoes_qs = inscricoes_qs.filter(pesagem_confirmada=False)
    elif filtro == 'ok':
        inscricoes_qs = inscricoes_qs.filter(pagamento_confirmado=True, pesagem_confirmada=True)

    from datetime import date, timedelta
    hoje = date.today()
    janela_pesagem_ativa = campeonato.janela_pesagem_ativa
    prazo_pagamento_ok = campeonato.prazo_pagamento_ok

    return render(request, 'campeonato/apoio_inscricoes.html', {
        'campeonato_atual': campeonato,
        'inscricoes': inscricoes_qs,
        'filtro': filtro,
        'janela_pesagem_ativa': janela_pesagem_ativa,
        'prazo_pagamento_ok': prazo_pagamento_ok,
        'total': inscricoes_qs.count(),
        'total_pago': InscricaoCampeonato.objects.filter(campeonato=campeonato, pagamento_confirmado=True).count(),
        'total_pesado': InscricaoCampeonato.objects.filter(campeonato=campeonato, pesagem_confirmada=True).count(),
    })


@require_POST
def apoio_confirmar_pagamento(request, pk):
    """Confirma (ou reverte) o pagamento de uma inscrição."""
    inscricao = get_object_or_404(InscricaoCampeonato, pk=pk)
    acao = request.POST.get('acao', 'confirmar')
    if acao == 'confirmar':
        from django.utils import timezone
        inscricao.pagamento_confirmado = True
        inscricao.pagamento_confirmado_em = timezone.now()
        inscricao.save(update_fields=['pagamento_confirmado', 'pagamento_confirmado_em'])
        messages.success(request, f'Pagamento de {inscricao.atleta.nome} confirmado.')
    else:
        inscricao.pagamento_confirmado = False
        inscricao.pagamento_confirmado_em = None
        inscricao.save(update_fields=['pagamento_confirmado', 'pagamento_confirmado_em'])
        messages.warning(request, f'Pagamento de {inscricao.atleta.nome} revertido.')
    return redirect(request.POST.get('next') or 'apoio_inscricoes')


@require_POST
def apoio_confirmar_pesagem(request, pk):
    """Registra o peso aferido e confirma a pesagem de uma inscrição."""
    inscricao = get_object_or_404(InscricaoCampeonato, pk=pk)
    acao = request.POST.get('acao', 'confirmar')
    if acao == 'confirmar':
        from django.utils import timezone
        import decimal
        peso_str = request.POST.get('peso_aferido', '').replace(',', '.').strip()
        try:
            peso = decimal.Decimal(peso_str)
        except decimal.InvalidOperation:
            messages.error(request, 'Peso inválido. Digite um número (ex: 72.5).')
            return redirect(request.POST.get('next') or 'apoio_inscricoes')
        inscricao.pesagem_confirmada = True
        inscricao.peso_aferido = peso
        inscricao.pesagem_realizada_em = timezone.now()
        inscricao.save(update_fields=['pesagem_confirmada', 'peso_aferido', 'pesagem_realizada_em'])
        messages.success(request, f'Pesagem de {inscricao.atleta.nome} confirmada: {peso} kg.')
    else:
        inscricao.pesagem_confirmada = False
        inscricao.peso_aferido = None
        inscricao.pesagem_realizada_em = None
        inscricao.save(update_fields=['pesagem_confirmada', 'peso_aferido', 'pesagem_realizada_em'])
        messages.warning(request, f'Pesagem de {inscricao.atleta.nome} revertida.')
    return redirect(request.POST.get('next') or 'apoio_inscricoes')


def apoio_validar(request, codigo):
    """Valida o QR Code de um atleta e realiza o check-in."""
    try:
        inscricao = InscricaoCampeonato.objects.select_related('atleta', 'categoria').get(codigo=codigo)
        atleta = inscricao.atleta
    except InscricaoCampeonato.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erro': 'Atleta não encontrado.'}, status=404)
        messages.error(request, 'QR Code inválido — atleta não encontrado.')
        return redirect('apoio_home')

    ja_fez_checkin = hasattr(inscricao, 'checkin')

    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            if not ja_fez_checkin:
                checkin = form.save(commit=False)
                checkin.atleta = atleta
                checkin.inscricao = inscricao
                checkin.save()
                messages.success(request, f'Check-in de {atleta.nome} realizado com sucesso!')
            else:
                messages.warning(request, f'{atleta.nome} já fez check-in anteriormente.')
            return redirect('apoio_home')
    else:
        form = CheckInForm()

    return render(request, 'campeonato/apoio_validar.html', {
        'atleta': atleta,
        'inscricao': inscricao,
        'ja_fez_checkin': ja_fez_checkin,
        'form': form,
    })


def apoio_checkin_ajax(request, codigo):
    """Retorna dados do atleta via AJAX para o scanner."""
    try:
        inscricao = InscricaoCampeonato.objects.select_related('atleta', 'categoria', 'checkin__baia').get(codigo=codigo)
        atleta = inscricao.atleta
    except InscricaoCampeonato.DoesNotExist:
        return JsonResponse({'ok': False, 'erro': 'Atleta não encontrado.'})

    return JsonResponse({
        'ok': True,
        'nome': atleta.nome,
        'academia': atleta.academia,
        'faixa': atleta.get_faixa_display(),
        'categoria': str(inscricao.categoria) if inscricao.categoria else '—',
        'modalidade': inscricao.get_modalidade_inscricao_display(),
        'tipo_documento': 'Documento de bolsa' if inscricao.modalidade_inscricao == 'bolsa' else 'Comprovante de pagamento',
        'url_documento': (
            inscricao.documento_bolsa.url if inscricao.modalidade_inscricao == 'bolsa' and inscricao.documento_bolsa
            else inscricao.comprovante_pagamento.url if inscricao.comprovante_pagamento
            else ''
        ),
        'peso': str(atleta.peso),
        'ja_fez_checkin': hasattr(inscricao, 'checkin'),
        'url_validar': f'/apoio/validar/{inscricao.codigo}/',
    })


# ===================== MESA DO ÁRBITRO =====================
def arbitro_cadastro(request):
    perfil = Arbitro.objects.filter(usuario=request.user).first() if request.user.is_authenticated else None
    if perfil and perfil.ativo:
        return redirect(nome_home_equipe(perfil))

    form = CadastroArbitroForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        user.email = form.cleaned_data['email']
        user.save(update_fields=['email'])
        Arbitro.objects.create(
            usuario=user,
            nome=form.cleaned_data['nome'],
            funcao=Arbitro.FUNCAO_ARBITRO,
            ativo=False,
        )
        messages.success(request, 'Cadastro de árbitro enviado com sucesso. Aguarde a aprovação da organização para acessar sua área.')
        return redirect('arbitro_login')

    return render(request, 'campeonato/arbitro_cadastro.html', {'form': form})


def _login_equipe(request, funcao, titulo_area, url_home, url_login, subtitulo):
    if request.user.is_authenticated:
        perfil_logado = Arbitro.objects.filter(usuario=request.user).first()
        if perfil_logado and not perfil_logado.ativo:
            messages.info(request, f'Seu cadastro de {perfil_logado.get_funcao_display().lower()} está pendente de aprovação da organização.')
            logout(request)
        elif (perfil_logado and perfil_logado.funcao == funcao) or request.user.is_staff or request.user.is_superuser:
            return redirect(url_home)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            perfil = Arbitro.objects.filter(usuario=user).first()
            if perfil and not perfil.ativo:
                messages.warning(request, f'Seu cadastro de {perfil.get_funcao_display().lower()} ainda não foi aprovado pela organização.')
            elif user.is_staff or user.is_superuser:
                login(request, user)
                return redirect(url_home)
            elif perfil and perfil.funcao == funcao:
                login(request, user)
                return redirect(url_home)
            elif perfil:
                messages.error(request, f'Este usuário está cadastrado como {perfil.get_funcao_display().lower()}, não como {titulo_area.lower()}.')
            else:
                messages.error(request, 'Usuário sem perfil da equipe vinculado.')
                return render(request, 'campeonato/arbitro_login.html', {
                    'titulo_area': titulo_area,
                    'subtitulo_area': subtitulo,
                    'url_login': url_login,
                })
        else:
            messages.error(request, f'Usuário ou senha inválidos para a área de {titulo_area.lower()}.')

    return render(request, 'campeonato/arbitro_login.html', {
        'titulo_area': titulo_area,
        'subtitulo_area': subtitulo,
        'url_login': url_login,
    })


def arbitro_login(request):
    return _login_equipe(request, Arbitro.FUNCAO_ARBITRO, 'Árbitro', 'arbitro_home', 'arbitro_login', 'Acesso do árbitro de tatame')


def mesario_login(request):
    return _login_equipe(request, Arbitro.FUNCAO_MESARIO, 'Mesário', 'mesario_home', 'mesario_login', 'Acesso de quem opera a mesa e lança a pontuação')


def arbitro_logout(request):
    logout(request)
    messages.success(request, 'Sessão do árbitro encerrada com sucesso.')
    return redirect('arbitro_login')


def mesario_logout(request):
    logout(request)
    messages.success(request, 'Sessão do mesário encerrada com sucesso.')
    return redirect('mesario_login')


def _home_equipe(request, funcao, url_login, area_titulo, area_subtitulo, rota_tatame, rota_logout, pode_operar):
    if not request.user.is_authenticated:
        messages.warning(request, f'Faça login para acessar a área de {area_titulo.lower()}.')
        return redirect(url_login)

    campeonato = get_campeonato_atual(request)
    arbitro = Arbitro.objects.filter(usuario=request.user, ativo=True, funcao=funcao).first()
    if not arbitro and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, f'Seu usuário não está vinculado a um perfil de {area_titulo.lower()}.')
        return redirect(url_login)

    if arbitro:
        vinculos = ArbitroTatame.objects.filter(arbitro=arbitro, campeonato=campeonato).select_related('tatame').order_by('tatame__numero')
        tatames = Tatame.objects.filter(pk__in=vinculos.values('tatame_id'), ativo=True).annotate(total_lutas=Count('lutas')).order_by('numero')
        historico_lutas = Luta.objects.filter(
            Q(arbitro=arbitro) | Q(iniciada_por=arbitro) | Q(finalizada_por=arbitro),
            chave__categoria__campeonato=campeonato,
        ).select_related('atleta1', 'atleta2', 'vencedor', 'tatame', 'chave__categoria', 'finalizada_por').distinct().order_by('-realizada_em', '-iniciada_em', '-id')[:20]
    else:
        vinculos = ArbitroTatame.objects.filter(campeonato=campeonato).select_related('arbitro', 'tatame').order_by('tatame__numero') if campeonato else ArbitroTatame.objects.none()
        tatames = Tatame.objects.filter(campeonato=campeonato, ativo=True).annotate(total_lutas=Count('lutas')).order_by('numero') if campeonato else Tatame.objects.none()
        historico_lutas = Luta.objects.filter(chave__categoria__campeonato=campeonato).select_related('atleta1', 'atleta2', 'vencedor', 'tatame', 'chave__categoria', 'finalizada_por').order_by('-realizada_em', '-id')[:20] if campeonato else Luta.objects.none()

    return render(request, 'campeonato/arbitro_home.html', {
        'arbitro': arbitro,
        'tatames': tatames,
        'vinculos': vinculos,
        'historico_lutas': historico_lutas,
        'campeonato_atual': campeonato,
        'area_titulo': area_titulo,
        'area_subtitulo': area_subtitulo,
        'rota_tatame': rota_tatame,
        'rota_logout': rota_logout,
        'pode_operar': pode_operar,
    })


def arbitro_home(request):
    return _home_equipe(request, Arbitro.FUNCAO_ARBITRO, 'arbitro_login', 'Árbitro', 'Acesso do árbitro de tatame e histórico de atuação', 'arbitro_tatame', 'arbitro_logout', False)


def mesario_home(request):
    return _home_equipe(request, Arbitro.FUNCAO_MESARIO, 'mesario_login', 'Mesário', 'Acesso da mesa de pontuação e dos tatames vinculados', 'mesario_tatame', 'mesario_logout', True)


def mesario_tatame(request, pk):
    return arbitro_tatame(request, pk)


def arbitro_tatame(request, pk):
    """Mesa do árbitro para um tatame específico."""
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login para acessar a mesa de pontuação.')
        return redirect('mesario_login')

    campeonato = get_campeonato_atual(request)
    tatame = get_object_or_404(Tatame, pk=pk, campeonato=campeonato)
    arbitro = get_perfil_equipe_atual(request)
    if not usuario_pode_operar_tatame(request, tatame):
        messages.error(request, 'Você não está vinculado a este tatame.')
        return redirect(nome_home_equipe(arbitro)) if arbitro else redirect('mesario_login')

    lutas = Luta.objects.filter(tatame=tatame).select_related(
        'atleta1', 'atleta2', 'vencedor', 'chave__categoria', 'arbitro', 'iniciada_por', 'finalizada_por'
    ).order_by('status', 'rodada', 'ordem')

    luta_atual = lutas.filter(status='em_andamento').first()
    proximas = lutas.filter(status='aguardando', resultado='pendente')
    finalizadas = lutas.filter(status='finalizada')

    # Ações agrupadas por categoria para o painel de pontuação por posição
    from collections import defaultdict
    grupos_acoes = defaultdict(list)
    for acao in TipoAcao.objects.filter(ativo=True).order_by('categoria', 'ordem', 'nome'):
        grupos_acoes[acao.categoria].append(acao)

    # Últimas ações da luta atual (para desfazer)
    ultimas_acoes = []
    if luta_atual:
        ultimas_acoes = luta_atual.acoes.select_related('atleta', 'tipo_acao').order_by('-registrado_em')[:8]

    return render(request, 'campeonato/arbitro_baia.html', {
        'arbitro': arbitro,
        'tatame': tatame,
        'luta_atual': luta_atual,
        'proximas': proximas,
        'finalizadas': finalizadas,
        'grupos_acoes': dict(grupos_acoes),
        'ultimas_acoes': ultimas_acoes,
        'home_url': 'mesario_home',
    })


@require_POST
def arbitro_iniciar_luta(request, pk):
    """Árbitro inicia uma luta (muda status para em_andamento)."""
    from django.utils import timezone
    luta = get_object_or_404(Luta, pk=pk)
    if not request.user.is_authenticated:
        messages.warning(request, 'Faça login para acessar a mesa de pontuação.')
        return redirect('mesario_login')
    if not luta.tatame or not usuario_pode_operar_tatame(request, luta.tatame):
        messages.error(request, 'Você não pode iniciar lutas deste tatame.')
        return redirect('mesario_home')

    arbitro = get_perfil_equipe_atual(request)
    if luta.status == 'aguardando':
        luta.status = 'em_andamento'
        luta.iniciada_em = timezone.now()
        if arbitro:
            luta.arbitro = arbitro
            luta.iniciada_por = arbitro
        luta.save()
        messages.success(request, f'Luta iniciada: {luta}')
    return redirect('mesario_tatame', pk=luta.tatame.pk)


@require_POST
def arbitro_atribuir_tatame(request, luta_pk):
    """Atribui um tatame a uma luta."""
    luta = get_object_or_404(Luta, pk=luta_pk)
    tatame_pk = request.POST.get('tatame_pk')
    tatame = get_object_or_404(Tatame, pk=tatame_pk, campeonato=luta.chave.categoria.campeonato)
    luta.tatame = tatame
    luta.save()
    messages.success(request, f'Luta atribuída ao {tatame}.')
    return redirect('chave_detalhe', pk=luta.chave.pk)


# ===================== PLACAR AO VIVO =====================

CAMPOS_PONTUACAO = {
    'pontos_atleta1', 'pontos_atleta2',
    'vantagens_atleta1', 'vantagens_atleta2',
    'penalizacoes_atleta1', 'penalizacoes_atleta2',
}


@require_POST
def arbitro_pontuar(request, pk):
    """Árbitro pontua durante a luta via AJAX. Salva incrementalmente."""
    if not request.user.is_authenticated:
        return JsonResponse({'erro': 'Não autenticado'}, status=403)

    luta = get_object_or_404(Luta, pk=pk)

    if luta.status != 'em_andamento':
        return JsonResponse({'erro': 'Luta não está em andamento'}, status=400)

    # Segurança: valida o campo e o árbitro
    if not (request.user.is_staff or request.user.is_superuser):
        arbitro = get_perfil_equipe_atual(request)
        if not arbitro:
            return JsonResponse({'erro': 'Perfil da equipe não encontrado'}, status=403)
        if luta.tatame and not usuario_pode_operar_tatame(request, luta.tatame):
            return JsonResponse({'erro': 'Sem permissão neste tatame'}, status=403)

    campo = request.POST.get('campo', '')
    try:
        delta = int(request.POST.get('delta', 0))
    except (ValueError, TypeError):
        return JsonResponse({'erro': 'Delta inválido'}, status=400)

    if campo not in CAMPOS_PONTUACAO:
        return JsonResponse({'erro': 'Campo inválido'}, status=400)

    # Aplica delta, mantém valor >= 0
    valor_atual = getattr(luta, campo)
    novo_valor = max(0, valor_atual + delta)
    setattr(luta, campo, novo_valor)
    luta.save(update_fields=[campo])

    return JsonResponse({
        'ok': True,
        'campo': campo,
        'valor': novo_valor,
        'pontos_atleta1': luta.pontos_atleta1,
        'pontos_atleta2': luta.pontos_atleta2,
        'vantagens_atleta1': luta.vantagens_atleta1,
        'vantagens_atleta2': luta.vantagens_atleta2,
        'penalizacoes_atleta1': luta.penalizacoes_atleta1,
        'penalizacoes_atleta2': luta.penalizacoes_atleta2,
    })


def api_placar_luta(request, pk):
    """Retorna o placar atual de uma luta em JSON (polling do telão)."""
    luta = get_object_or_404(Luta, pk=pk)
    a1 = luta.atleta1
    a2 = luta.atleta2
    return JsonResponse({
        'luta_id': luta.pk,
        'status': luta.status,
        'resultado': luta.resultado,
        'rodada': luta.rodada,
        'categoria': str(luta.chave.categoria) if luta.chave_id else '',
        'atleta1': {'id': a1.pk, 'nome': a1.nome, 'academia': a1.academia, 'faixa': a1.get_faixa_display()} if a1 else None,
        'atleta2': {'id': a2.pk, 'nome': a2.nome, 'academia': a2.academia, 'faixa': a2.get_faixa_display()} if a2 else None,
        'pontos_atleta1': luta.pontos_atleta1,
        'pontos_atleta2': luta.pontos_atleta2,
        'vantagens_atleta1': luta.vantagens_atleta1,
        'vantagens_atleta2': luta.vantagens_atleta2,
        'penalizacoes_atleta1': luta.penalizacoes_atleta1,
        'penalizacoes_atleta2': luta.penalizacoes_atleta2,
        'vencedor_id': luta.vencedor_id,
    })


def placar_tatame(request, pk):
    """Tela pública de placar em tempo real para um tatame (para projetar no telão)."""
    campeonato = get_campeonato_atual(request)
    tatame = get_object_or_404(Tatame, pk=pk)
    luta_atual = Luta.objects.filter(
        tatame=tatame, status='em_andamento'
    ).select_related('atleta1', 'atleta2', 'chave__categoria').first()

    return render(request, 'campeonato/placar_tatame.html', {
        'tatame': tatame,
        'luta_atual': luta_atual,
        'campeonato_atual': campeonato,
    })


def api_placar_tatame(request, pk):
    """API de polling: retorna a luta em andamento do tatame (ou a última finalizada)."""
    tatame = get_object_or_404(Tatame, pk=pk)
    luta = Luta.objects.filter(
        tatame=tatame, status='em_andamento'
    ).select_related('atleta1', 'atleta2', 'chave__categoria').first()

    # Se não há em andamento, mostra a última finalizada (para o win overlay)
    if not luta:
        luta = Luta.objects.filter(
            tatame=tatame, status='finalizada'
        ).select_related('atleta1', 'atleta2', 'chave__categoria').order_by('-pk').first()

    if not luta:
        return JsonResponse({'luta_id': None})

    a1 = luta.atleta1
    a2 = luta.atleta2
    vencedor = luta.vencedor if hasattr(luta, 'vencedor') else None
    if not vencedor and luta.vencedor_id:
        from campeonato.models import Atleta
        try:
            vencedor = Atleta.objects.get(pk=luta.vencedor_id)
        except Exception:
            pass
    return JsonResponse({
        'luta_id': luta.pk,
        'status': luta.status,
        'resultado': luta.resultado,
        'rodada': luta.rodada,
        'categoria': str(luta.chave.categoria) if luta.chave_id else '',
        'atleta1': {'id': a1.pk, 'nome': a1.nome, 'academia': a1.academia, 'faixa': a1.get_faixa_display()} if a1 else None,
        'atleta2': {'id': a2.pk, 'nome': a2.nome, 'academia': a2.academia, 'faixa': a2.get_faixa_display()} if a2 else None,
        'pontos_atleta1': luta.pontos_atleta1,
        'pontos_atleta2': luta.pontos_atleta2,
        'vantagens_atleta1': luta.vantagens_atleta1,
        'vantagens_atleta2': luta.vantagens_atleta2,
        'penalizacoes_atleta1': luta.penalizacoes_atleta1,
        'penalizacoes_atleta2': luta.penalizacoes_atleta2,
        'vencedor_id': luta.vencedor_id,
        'vencedor_nome': vencedor.nome if vencedor else '',
        'iniciada_em_ts': luta.iniciada_em.timestamp() if luta.iniciada_em else None,
        'duracao_segundos': luta.chave.categoria.duracao_segundos if luta.chave_id and luta.chave.categoria_id else 300,
    })


# ===================== AÇÕES POR POSIÇÃO =====================

def _acoes_para_template():
    """Retorna ações agrupadas por categoria para o template da mesa."""
    from collections import defaultdict
    grupos = defaultdict(list)
    for acao in TipoAcao.objects.filter(ativo=True).order_by('categoria', 'ordem', 'nome'):
        grupos[acao.categoria].append(acao)
    return dict(grupos)


@require_POST
def arbitro_registrar_acao(request, luta_pk):
    """
    Árbitro registra uma ação/posição durante a luta (AJAX).
    - Credita pontos/vantagem/penalização automaticamente no placar.
    - Para finalizações: encerra a luta com resultado='finalizacao'.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'erro': 'Não autenticado'}, status=403)

    luta = get_object_or_404(Luta, pk=luta_pk)

    if luta.status != 'em_andamento':
        return JsonResponse({'erro': 'Luta não está em andamento'}, status=400)

    arbitro = get_perfil_equipe_atual(request)
    if not (request.user.is_staff or request.user.is_superuser):
        if not arbitro:
            return JsonResponse({'erro': 'Perfil da equipe não encontrado'}, status=403)
        if luta.tatame and not usuario_pode_operar_tatame(request, luta.tatame):
            return JsonResponse({'erro': 'Sem permissão neste tatame'}, status=403)

    tipo_acao_pk = request.POST.get('tipo_acao')
    atleta_num = request.POST.get('atleta')  # '1' ou '2'
    observacao = request.POST.get('observacao', '').strip()[:300]

    tipo_acao = get_object_or_404(TipoAcao, pk=tipo_acao_pk, ativo=True)

    if atleta_num not in ('1', '2'):
        return JsonResponse({'erro': 'atleta deve ser 1 ou 2'}, status=400)

    atleta = luta.atleta1 if atleta_num == '1' else luta.atleta2

    # Atualiza o placar conforme a categoria da ação
    campos_update = []
    from django.utils import timezone

    if tipo_acao.categoria == 'pontos' and tipo_acao.pontos > 0:
        campo = f'pontos_atleta{atleta_num}'
        setattr(luta, campo, getattr(luta, campo) + tipo_acao.pontos)
        campos_update.append(campo)

    elif tipo_acao.categoria == 'vantagem':
        campo = f'vantagens_atleta{atleta_num}'
        setattr(luta, campo, getattr(luta, campo) + 1)
        campos_update.append(campo)

    elif tipo_acao.categoria == 'penalizacao':
        campo = f'penalizacoes_atleta{atleta_num}'
        setattr(luta, campo, getattr(luta, campo) + 1)
        campos_update.append(campo)
        # Penalização do adversário gera vantagem para o outro
        outro = '2' if atleta_num == '1' else '1'
        campo_van = f'vantagens_atleta{outro}'
        setattr(luta, campo_van, getattr(luta, campo_van) + 1)
        campos_update.append(campo_van)

    elif tipo_acao.categoria == 'finalizacao':
        # Encerra a luta por finalização
        luta.vencedor = atleta
        luta.resultado = 'finalizacao'
        luta.status = 'finalizada'
        luta.realizada_em = timezone.now()
        if arbitro:
            luta.finalizada_por = arbitro
        campos_update += ['vencedor', 'resultado', 'status', 'realizada_em', 'finalizada_por']

    if campos_update:
        luta.save(update_fields=campos_update)

    # Registra a ação no histórico
    AcaoLuta.objects.create(
        luta=luta,
        atleta=atleta,
        tipo_acao=tipo_acao,
        registrado_por=arbitro,
        observacao=observacao,
    )

    return JsonResponse({
        'ok': True,
        'categoria': tipo_acao.categoria,
        'acao': tipo_acao.nome,
        'pontos': tipo_acao.pontos,
        'encerrou': tipo_acao.categoria == 'finalizacao',
        'pontos_atleta1': luta.pontos_atleta1,
        'pontos_atleta2': luta.pontos_atleta2,
        'vantagens_atleta1': luta.vantagens_atleta1,
        'vantagens_atleta2': luta.vantagens_atleta2,
        'penalizacoes_atleta1': luta.penalizacoes_atleta1,
        'penalizacoes_atleta2': luta.penalizacoes_atleta2,
    })


@require_POST
def arbitro_desfazer_acao(request, acao_pk):
    """Remove a última ação registrada e reverte o placar (desfazer)."""
    if not request.user.is_authenticated:
        return JsonResponse({'erro': 'Não autenticado'}, status=403)

    acao = get_object_or_404(AcaoLuta, pk=acao_pk)
    luta = acao.luta

    if luta.status == 'finalizada' and acao.tipo_acao.categoria != 'finalizacao':
        return JsonResponse({'erro': 'Luta já finalizada'}, status=400)

    arbitro = get_perfil_equipe_atual(request)
    if not (request.user.is_staff or request.user.is_superuser):
        if luta.tatame and not usuario_pode_operar_tatame(request, luta.tatame):
            return JsonResponse({'erro': 'Sem permissão'}, status=403)

    atleta_num = '1' if acao.atleta == luta.atleta1 else '2'
    tipo = acao.tipo_acao
    campos_update = []

    if tipo.categoria == 'pontos' and tipo.pontos > 0:
        campo = f'pontos_atleta{atleta_num}'
        setattr(luta, campo, max(0, getattr(luta, campo) - tipo.pontos))
        campos_update.append(campo)

    elif tipo.categoria == 'vantagem':
        campo = f'vantagens_atleta{atleta_num}'
        setattr(luta, campo, max(0, getattr(luta, campo) - 1))
        campos_update.append(campo)

    elif tipo.categoria == 'penalizacao':
        campo = f'penalizacoes_atleta{atleta_num}'
        setattr(luta, campo, max(0, getattr(luta, campo) - 1))
        campos_update.append(campo)
        outro = '2' if atleta_num == '1' else '1'
        campo_van = f'vantagens_atleta{outro}'
        setattr(luta, campo_van, max(0, getattr(luta, campo_van) - 1))
        campos_update.append(campo_van)

    elif tipo.categoria == 'finalizacao':
        # Reverte o encerramento
        luta.vencedor = None
        luta.resultado = 'pendente'
        luta.status = 'em_andamento'
        luta.realizada_em = None
        luta.finalizada_por = None
        campos_update += ['vencedor', 'resultado', 'status', 'realizada_em', 'finalizada_por']

    if campos_update:
        luta.save(update_fields=campos_update)

    acao.delete()

    return JsonResponse({
        'ok': True,
        'pontos_atleta1': luta.pontos_atleta1,
        'pontos_atleta2': luta.pontos_atleta2,
        'vantagens_atleta1': luta.vantagens_atleta1,
        'vantagens_atleta2': luta.vantagens_atleta2,
        'penalizacoes_atleta1': luta.penalizacoes_atleta1,
        'penalizacoes_atleta2': luta.penalizacoes_atleta2,
    })


def relatorio_luta(request, pk):
    """Relatório detalhado de ações de uma luta — acessível por árbitro, atleta e organização."""
    luta = get_object_or_404(
        Luta.objects.select_related(
            'atleta1', 'atleta2', 'vencedor', 'chave__categoria__campeonato',
            'arbitro', 'iniciada_por', 'finalizada_por', 'tatame',
        ),
        pk=pk,
    )
    acoes = luta.acoes.select_related('atleta', 'tipo_acao', 'registrado_por').order_by('registrado_em')

    # Estatísticas por atleta
    def stats(atleta):
        acs = acoes.filter(atleta=atleta)
        return {
            'pontos_acoes': sum(a.tipo_acao.pontos for a in acs if a.tipo_acao.categoria == 'pontos'),
            'vantagens': acs.filter(tipo_acao__categoria='vantagem').count(),
            'penalizacoes': acs.filter(tipo_acao__categoria='penalizacao').count(),
            'finalizacoes': acs.filter(tipo_acao__categoria='finalizacao').count(),
            'acoes': list(acs),
        }

    return render(request, 'campeonato/relatorio_luta.html', {
        'luta': luta,
        'acoes': acoes,
        'stats_a1': stats(luta.atleta1) if luta.atleta1 else {},
        'stats_a2': stats(luta.atleta2) if luta.atleta2 else {},
    })

