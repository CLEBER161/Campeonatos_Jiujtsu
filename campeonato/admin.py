from django.contrib import admin
from .models import Atleta, Categoria, Chave, Luta, Baia, CheckIn, Tatame, Campeonato, InscricaoCampeonato, Arbitro, ArbitroTatame


@admin.register(Campeonato)
class CampeonatoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_evento', 'local', 'inscricoes_abertas', 'ativo']
    list_filter = ['inscricoes_abertas', 'ativo']
    search_fields = ['nome', 'local']


@admin.register(Atleta)
class AtletaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'usuario', 'faixa', 'peso', 'sexo', 'academia', 'categoria']
    list_filter = ['faixa', 'sexo', 'academia', 'categoria']
    search_fields = ['nome', 'academia', 'usuario__username']


@admin.register(InscricaoCampeonato)
class InscricaoCampeonatoAdmin(admin.ModelAdmin):
    list_display = ['atleta', 'campeonato', 'categoria', 'criado_em']
    list_filter = ['campeonato', 'categoria']
    search_fields = ['atleta__nome', 'campeonato__nome']


@admin.register(Arbitro)
class ArbitroAdmin(admin.ModelAdmin):
    list_display = ['nome', 'usuario', 'ativo', 'criado_em']
    list_filter = ['ativo']
    search_fields = ['nome', 'usuario__username']


@admin.register(ArbitroTatame)
class ArbitroTatameAdmin(admin.ModelAdmin):
    list_display = ['arbitro', 'campeonato', 'tatame', 'criado_em']
    list_filter = ['campeonato', 'tatame']
    search_fields = ['arbitro__nome', 'tatame__nome', 'campeonato__nome']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'campeonato', 'faixa', 'sexo', 'peso_min', 'peso_max', 'idade_min', 'idade_max']
    list_filter = ['campeonato', 'faixa', 'sexo']


@admin.register(Chave)
class ChaveAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'tatame', 'criada_em']


@admin.register(Luta)
class LutaAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'chave',
        'tatame',
        'arbitro',
        'status',
        'resultado',
        'pontos_atleta1',
        'pontos_atleta2',
        'vantagens_atleta1',
        'vantagens_atleta2',
        'penalizacoes_atleta1',
        'penalizacoes_atleta2',
        'vencedor',
        'rodada',
    ]
    list_filter = ['resultado', 'status', 'rodada', 'tatame', 'arbitro']


@admin.register(Baia)
class BaiaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nome', 'campeonato', 'ativa']
    list_filter = ['campeonato', 'ativa']


@admin.register(Tatame)
class TatameAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nome', 'campeonato', 'ativo']
    list_filter = ['campeonato', 'ativo']


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ['atleta', 'inscricao', 'baia', 'realizado_em', 'validado_por']
    list_filter = ['baia', 'inscricao__campeonato']
    search_fields = ['atleta__nome']

