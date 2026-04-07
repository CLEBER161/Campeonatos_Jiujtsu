from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('espaco-atletas/', views.espaco_atletas, name='espaco_atletas'),
    path('organizacao/login/', views.organizacao_login, name='organizacao_login'),
    path('organizacao/logout/', views.organizacao_logout, name='organizacao_logout'),
    path('organizacao/', views.organizacao_home, name='organizacao_home'),
    path('organizacao/campeonatos/', views.organizacao_campeonatos, name='organizacao_campeonatos'),
    path('organizacao/categorias/', views.organizacao_categorias, name='organizacao_categorias'),
    path('organizacao/estrutura/', views.organizacao_estrutura, name='organizacao_estrutura'),
    path('organizacao/arbitros/', views.organizacao_arbitros, name='organizacao_arbitros'),
    path('organizacao/campeonatos/novo/', views.organizacao_criar_campeonato, name='organizacao_criar_campeonato'),
    path('organizacao/campeonatos/selecionar/', views.organizacao_selecionar_campeonato, name='organizacao_selecionar_campeonato'),
    path('organizacao/categorias-padrao/', views.organizacao_criar_categorias_padrao, name='organizacao_criar_categorias_padrao'),
    path('organizacao/categorias-completas/', views.organizacao_gerar_categorias_completas, name='organizacao_gerar_categorias_completas'),
    path('organizacao/baias/nova/', views.organizacao_criar_baia, name='organizacao_criar_baia'),
    path('organizacao/tatames/novo/', views.organizacao_criar_tatame, name='organizacao_criar_tatame'),
    path('organizacao/tatames/rebalancear/', views.organizacao_rebalancear_tatames, name='organizacao_rebalancear_tatames'),
    path('organizacao/arbitros/novo/', views.organizacao_criar_arbitro, name='organizacao_criar_arbitro'),
    path('organizacao/mesarios/credenciais/', views.organizacao_credenciais_mesarios, name='organizacao_credenciais_mesarios'),
    path('organizacao/arbitros/vincular/', views.organizacao_vincular_arbitro_tatame, name='organizacao_vincular_arbitro_tatame'),
    path('organizacao/arbitros/vinculos/<int:pk>/remover/', views.organizacao_remover_vinculo_arbitro, name='organizacao_remover_vinculo_arbitro'),
    path('atleta/cadastro/', views.atleta_cadastro, name='atleta_cadastro'),
    path('atleta/login/', views.atleta_login, name='atleta_login'),
    path('atleta/logout/', views.atleta_logout, name='atleta_logout'),
    path('atleta/minha-area/', views.minha_area_atleta, name='minha_area_atleta'),
    path('atleta/campeonatos/<int:campeonato_pk>/inscrever/', views.atleta_inscrever_campeonato, name='atleta_inscrever_campeonato'),
    path('atleta/tatames-tempo-real/', views.atleta_tatames_tempo_real, name='atleta_tatames_tempo_real'),
    path('atletas/prever-categoria/', views.atleta_prever_categoria, name='atleta_prever_categoria'),

    # Atletas
    path('atletas/', views.atleta_lista, name='atleta_lista'),
    path('atletas/novo/', views.atleta_criar, name='atleta_criar'),
    path('atletas/<int:pk>/', views.atleta_detalhe, name='atleta_detalhe'),
    path('atletas/<int:pk>/editar/', views.atleta_editar, name='atleta_editar'),
    path('atletas/<int:pk>/excluir/', views.atleta_excluir, name='atleta_excluir'),
    path('atletas/<int:pk>/credencial/', views.atleta_credencial, name='atleta_credencial'),
    path('atletas/<int:pk>/chaveamento/', views.atleta_chaveamento, name='atleta_chaveamento'),
    path('atletas/<int:pk>/ranking/', views.atleta_ranking, name='atleta_ranking'),

    # Categorias
    path('categorias/', views.categoria_lista, name='categoria_lista'),
    path('categorias/nova/', views.categoria_criar, name='categoria_criar'),
    path('categorias/<int:pk>/editar/', views.categoria_editar, name='categoria_editar'),
    path('categorias/<int:pk>/excluir/', views.categoria_excluir, name='categoria_excluir'),
    path('categorias/<int:categoria_pk>/gerar-chave/', views.chave_gerar, name='chave_gerar'),

    # Chaves e Lutas
    path('chaves/<int:pk>/', views.chave_detalhe, name='chave_detalhe'),
    path('chaves/<int:pk>/tatames/', views.organizacao_tatames_chave, name='organizacao_tatames_chave'),
    path('lutas/<int:pk>/resultado/', views.luta_resultado, name='luta_resultado'),
    path('lutas/<int:luta_pk>/atribuir-tatame/', views.arbitro_atribuir_tatame, name='arbitro_atribuir_tatame'),

    # Portal Apoio
    path('apoio/', views.apoio_home, name='apoio_home'),
    path('apoio/inscricoes/', views.apoio_inscricoes, name='apoio_inscricoes'),
    path('apoio/inscricoes/<int:pk>/pagamento/', views.apoio_confirmar_pagamento, name='apoio_confirmar_pagamento'),
    path('apoio/inscricoes/<int:pk>/pesagem/', views.apoio_confirmar_pesagem, name='apoio_confirmar_pesagem'),
    path('apoio/validar/<uuid:codigo>/', views.apoio_validar, name='apoio_validar'),
    path('apoio/ajax/<uuid:codigo>/', views.apoio_checkin_ajax, name='apoio_checkin_ajax'),

    # Mesa do Árbitro
    path('arbitro/cadastro/', views.arbitro_cadastro, name='arbitro_cadastro'),
    path('arbitro/login/', views.arbitro_login, name='arbitro_login'),
    path('arbitro/logout/', views.arbitro_logout, name='arbitro_logout'),
    path('mesario/login/', views.mesario_login, name='mesario_login'),
    path('mesario/logout/', views.mesario_logout, name='mesario_logout'),
    path('organizacao/arbitros/<int:pk>/status/', views.organizacao_status_arbitro, name='organizacao_status_arbitro'),
    path('arbitro/', views.arbitro_home, name='arbitro_home'),
    path('mesario/', views.mesario_home, name='mesario_home'),
    path('arbitro/tatame/<int:pk>/', views.arbitro_tatame, name='arbitro_tatame'),
    path('mesario/tatame/<int:pk>/', views.mesario_tatame, name='mesario_tatame'),
    path('arbitro/luta/<int:pk>/iniciar/', views.arbitro_iniciar_luta, name='arbitro_iniciar_luta'),
    path('arbitro/luta/<int:pk>/pontuar/', views.arbitro_pontuar, name='arbitro_pontuar'),
    path('api/luta/<int:pk>/placar/', views.api_placar_luta, name='api_placar_luta'),
    path('tatame/<int:pk>/placar/', views.placar_tatame, name='placar_tatame'),
    path('tatame/<int:pk>/placar/api/', views.api_placar_tatame, name='api_placar_tatame'),

    # Ações por posição
    path('lutas/<int:luta_pk>/acoes/', views.arbitro_registrar_acao, name='arbitro_registrar_acao'),
    path('acoes/<int:acao_pk>/desfazer/', views.arbitro_desfazer_acao, name='arbitro_desfazer_acao'),
    path('lutas/<int:pk>/relatorio/', views.relatorio_luta, name='relatorio_luta'),
]
