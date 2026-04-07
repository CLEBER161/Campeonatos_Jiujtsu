"""
Gera o arquivo Manual_Sistema_Campeonato_JiuJitsu.docx
Execute: python gerar_manual.py
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# ── Estilos de página ─────────────────────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Cm(21)
section.page_height = Cm(29.7)
section.left_margin   = Cm(3)
section.right_margin  = Cm(2)
section.top_margin    = Cm(2.5)
section.bottom_margin = Cm(2.5)

# ── Cores ─────────────────────────────────────────────────────────────────────
COR_TITULO   = RGBColor(0xC0, 0x39, 0x2B)   # vermelho jiu-jitsu
COR_SECAO    = RGBColor(0x1A, 0x5A, 0x96)   # azul escuro
COR_CINZA    = RGBColor(0x55, 0x55, 0x55)
COR_BRANCO   = RGBColor(0xFF, 0xFF, 0xFF)
COR_HEADER   = RGBColor(0x1A, 0x5A, 0x96)

def set_run_color(run, cor):
    run.font.color.rgb = cor

def cell_bg(cell, hex_color):
    """Define cor de fundo de célula."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def heading(doc, texto, nivel=1):
    """Adiciona título formatado manualmente."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18 if nivel == 1 else 10)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run(texto)
    run.bold = True
    if nivel == 1:
        run.font.size = Pt(16)
        set_run_color(run, COR_TITULO)
    elif nivel == 2:
        run.font.size = Pt(13)
        set_run_color(run, COR_SECAO)
    else:
        run.font.size = Pt(11.5)
        set_run_color(run, COR_CINZA)
    return p

def body(doc, texto, bold=False, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(texto)
    run.font.size = Pt(11)
    run.bold   = bold
    run.italic = italic
    return p

def bullet(doc, texto, nivel=1):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(0.5 * nivel)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(texto)
    run.font.size = Pt(11)
    return p

def url(doc, texto, link):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(f'{texto}: ')
    r.bold = True
    r.font.size = Pt(11)
    r2 = p.add_run(link)
    r2.font.size   = Pt(11)
    r2.font.color.rgb = RGBColor(0x1A, 0x5A, 0x96)
    r2.underline   = True
    return p

def linha(doc):
    p = doc.add_paragraph('─' * 72)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    run = p.runs[0]
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

def tabela_acesso(doc, dados, cabecalho):
    """Cria tabela formatada."""
    t = doc.add_table(rows=1, cols=len(cabecalho))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.style = 'Table Grid'
    hdr = t.rows[0].cells
    for i, h in enumerate(cabecalho):
        hdr[i].text = h
        cell_bg(hdr[i], '1A5A96')
        for run in hdr[i].paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = COR_BRANCO
            run.font.size = Pt(10)
    for linha_dados in dados:
        row = t.add_row().cells
        for i, val in enumerate(linha_dados):
            row[i].text = val
            for run in row[i].paragraphs[0].runs:
                run.font.size = Pt(10)
    doc.add_paragraph()
    return t

# ══════════════════════════════════════════════════════════════════════════════
# CAPA
# ══════════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(60)
r = p.add_run('SISTEMA DE CAMPEONATO DE JIU-JITSU')
r.bold = True
r.font.size = Pt(22)
set_run_color(r, COR_TITULO)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run('Manual Completo de Funcionalidades')
r2.font.size = Pt(14)
set_run_color(r2, COR_SECAO)

p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
p3.paragraph_format.space_before = Pt(60)
r3 = p3.add_run(f'Versão 1.0  ·  {datetime.date.today().strftime("%B de %Y")}')
r3.font.size = Pt(11)
set_run_color(r3, COR_CINZA)
r3.italic = True

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SUMÁRIO (manual)
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, 'SUMÁRIO', 1)
sumario_itens = [
    '1. Visão Geral do Sistema',
    '2. Módulo de Organização',
    '   2.1  Gerenciar Campeonatos',
    '   2.2  Categorias',
    '   2.3  Tatames e Baias',
    '   2.4  Equipe (Mesários e Árbitros)',
    '   2.5  Estrutura e Chaveamento',
    '3. Módulo de Mesa e Arbitragem',
    '   3.1  Login do Mesário',
    '   3.2  Login do Árbitro',
    '   3.3  Mesa ao Vivo',
    '   3.4  Pontuação Rápida',
    '   3.5  Pontuação por Posição / Técnica',
    '   3.6  Relatório de Luta',
    '4. Telão de Placar (Projeção)',
    '5. Módulo do Atleta',
    '   5.1  Cadastro e Login',
    '   5.2  Inscrição em Campeonato',
    '   5.3  Chaveamento e Resultados',
    '   5.4  Credencial e QR Code',
    '6. Módulo de Apoio / Credenciamento',
    '7. Ranking',
    '8. Referência de URLs',
    '9. Dados de Teste (Simulação)',
    '10. Comandos de Gerenciamento',
]
for item in sumario_itens:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)
    p.runs[0].font.size = Pt(11)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# 1. VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '1. Visão Geral do Sistema', 1)
body(doc,
    'O Sistema de Campeonato de Jiu-Jitsu é uma aplicação web desenvolvida em Django '
    'que gerencia todo o ciclo de vida de um torneio de jiu-jitsu: desde o cadastro de '
    'atletas e a organização das categorias até a pontuação em tempo real e a emissão de '
    'relatórios de luta.')

body(doc, 'O sistema é dividido em cinco perfis de acesso:', bold=True)
bullet(doc, 'Organização — administra campeonatos, categorias, tatames e equipe operacional.')
bullet(doc, 'Mesário — opera a mesa de pontuação no tatame (inicia luta e lança pontos).')
bullet(doc, 'Árbitro — perfil separado para consulta e acompanhamento do tatame.')
bullet(doc, 'Atleta — se inscreve, acompanha o chaveamento e visualiza sua credencial.')
bullet(doc, 'Apoio / Credenciamento — valida a entrada de atletas via QR code.')

body(doc, 'Tecnologias utilizadas:', bold=True)
bullet(doc, 'Backend: Django 6 (Python 3.12)')
bullet(doc, 'Banco de dados: SQLite (desenvolvimento) / PostgreSQL (produção)')
bullet(doc, 'Frontend: HTML5, CSS3, JavaScript puro (sem frameworks externos)')
bullet(doc, 'Comunicação em tempo real: AJAX com polling JSON a cada 2 segundos')

# ══════════════════════════════════════════════════════════════════════════════
# 2. MÓDULO DE ORGANIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '2. Módulo de Organização', 1)
body(doc,
    'Acessado pelo staff (superusuário ou usuário com is_staff=True). '
    'Controla toda a estrutura do evento.')

heading(doc, '2.1 Gerenciar Campeonatos', 2)
bullet(doc, 'Criar, editar e excluir campeonatos com nome, data, local e quantidade de tatames.')
bullet(doc, 'Ao criar campeonato, o sistema gera automaticamente os tatames e um mesário por tatame.')
bullet(doc, 'Senha dos mesários é gerada automaticamente e fica disponível para impressão.')
bullet(doc, 'Definir o campeonato "atual" para que os demais módulos o utilizem automaticamente.')
bullet(doc, 'Visualizar estatísticas gerais: total de atletas, lutas, categorias e tatames.')

heading(doc, '2.2 Categorias', 2)
bullet(doc, 'Cadastrar categorias com faixa, gênero, peso e idade.')
bullet(doc, 'Categorias padrão pré-configuradas para jiu-jitsu (branca, azul, roxa, marrom, preta).')
bullet(doc, 'Vincular categorias a campeonatos.')
bullet(doc, 'Visualizar atletas inscritos por categoria.')

heading(doc, '2.3 Tatames e Baias', 2)
bullet(doc, 'Criar tatames numerados e vinculá-los ao campeonato.')
bullet(doc, 'Cada tatame pode ter múltiplas baias (áreas de luta).')
bullet(doc, 'Atribuir lutas a tatames manualmente ou via chaveamento automático.')
bullet(doc, 'Visualizar a fila de lutas de cada tatame em tempo real.')

heading(doc, '2.4 Equipe (Mesários e Árbitros)', 2)
bullet(doc, 'Cadastrar perfis da equipe com função: Mesário ou Árbitro.')
bullet(doc, 'Para mesário, é possível gerar senha automática no cadastro.')
bullet(doc, 'Vincular mesários aos tatames do campeonato.')
bullet(doc, 'Imprimir folha de credenciais das mesas com usuário e senha por tatame.')
bullet(doc, 'Desvincular perfis de mesa/tatame a qualquer momento.')

heading(doc, '2.5 Estrutura e Chaveamento', 2)
bullet(doc, 'Gerar chaveamento por eliminação simples para cada categoria.')
bullet(doc, 'Visualizar e gerenciar a árvore de lutas (chaves).')
bullet(doc, 'Avançar lutas para a próxima rodada automaticamente após registro do resultado.')
bullet(doc, 'Atribuir lutas a tatames e baias.')
bullet(doc, 'Rebalancear lutas por escopo: apenas rodada 1 ou todas as rodadas pendentes.')
bullet(doc, 'Rebalanceamento prioriza tatame com menor fila e agrupa categorias por tatame.')

# ══════════════════════════════════════════════════════════════════════════════
# 3. MÓDULO DO ÁRBITRO
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '3. Módulo de Mesa e Arbitragem', 1)
body(doc,
    'É o coração operacional do sistema durante o evento. '
    'A operação da mesa é feita pelo mesário, enquanto o árbitro possui acesso separado.')

heading(doc, '3.1 Login do Mesário', 2)
url(doc, 'Login do mesário', 'http://127.0.0.1:8000/mesario/login/')
bullet(doc, 'O mesário entra com usuário e senha cadastrados pela organização.')
bullet(doc, 'Após o login, a tela inicial exibe os tatames vinculados ao perfil.')
bullet(doc, 'É o perfil que opera a mesa, lança pontuação e inicia lutas.')

heading(doc, '3.2 Login do Árbitro', 2)
url(doc, 'Login do árbitro', 'http://127.0.0.1:8000/arbitro/login/')
bullet(doc, 'Acesso separado para árbitros no sistema.')
bullet(doc, 'Permite consulta e acompanhamento com segregação de função.')

body(doc, 'Credenciais de teste (simulação):', bold=True)
tabela_acesso(doc,
    [
        ('mesario1', 'senha123', 'Mesário - Tatame 1'),
        ('mesario2', 'senha123', 'Mesário - Tatame 2'),
        ('mesario3', 'senha123', 'Mesário - Tatame 3'),
        ('mesario4', 'senha123', 'Mesário - Tatame 4'),
        ('arbitro1', 'senha123', 'Tatame 1'),
        ('arbitro2', 'senha123', 'Tatame 2'),
        ('arbitro3', 'senha123', 'Tatame 3'),
        ('arbitro4', 'senha123', 'Tatame 4'),
    ],
    ['Usuário', 'Senha', 'Perfil']
)

heading(doc, '3.3 Mesa ao Vivo', 2)
url(doc, 'Mesa do tatame', 'http://127.0.0.1:8000/mesario/tatame/<id>/')
bullet(doc, 'Exibe a luta em andamento com nomes, faixas e academias dos atletas.')
bullet(doc, 'Placar atualizado em tempo real (AJAX, sem recarregar a página).')
bullet(doc, 'Lista das próximas lutas na fila do tatame.')
bullet(doc, 'Botão para iniciar a próxima luta.')
bullet(doc, 'Botão "Telão" para abrir a projeção pública em nova aba.')
bullet(doc, 'Link para o relatório detalhado de qualquer luta já finalizada.')

heading(doc, '3.4 Pontuação Rápida', 2)
body(doc,
    'Modo ⚡ Pontuação Rápida — ideal para árbitros experientes que '
    'querem lançar pontos diretamente sem selecionar a técnica.')
bullet(doc, 'Botões +2, +3, +4 de pontos para cada atleta.')
bullet(doc, 'Botões +1 vantagem e +1 penalização individuais.')
bullet(doc, 'Botão "−" para corrigir erros de lançamento (decremento).')
bullet(doc, 'Penalização aplicada a um atleta automaticamente gera vantagem para o adversário.')
bullet(doc, 'Todos os lançamentos são salvos via AJAX sem recarregar a página.')

heading(doc, '3.5 Pontuação por Posição / Técnica', 2)
body(doc,
    'Modo 🥋 Por Posição — registra a técnica exata que gerou a pontuação, '
    'gerando histórico completo para relatórios.')
bullet(doc, 'Seletor de atleta (azul / vermelho).')
bullet(doc, 'Abas de categoria: Pontos · Vantagem · Penalização · Finalização.')
bullet(doc, '63 técnicas cadastradas, organizadas em 4 categorias:')
bullet(doc, 'Pontos (20): derrubadas, raspagens, passagens de guarda, monte, costas, joelho na barriga.', nivel=2)
bullet(doc, 'Vantagem (7): tentativas incompletas, derrubada incompleta, quase-finalização etc.', nivel=2)
bullet(doc, 'Penalização (9): passividade, fugir da área, falta de combatividade etc.', nivel=2)
bullet(doc, 'Finalização (27): estrangulamentos, chaves de braço, chaves de perna.', nivel=2)
bullet(doc, 'Ao registrar uma finalização, a luta é encerrada automaticamente com o vencedor definido.')
bullet(doc, 'Seção "Últimas ações" com botão ↩ Desfazer para reverter o último lançamento e o placar.')
bullet(doc, 'A preferência de modo (Rápido ou Por Posição) é salva no navegador por tatame.')

heading(doc, '3.6 Relatório de Luta', 2)
url(doc, 'Relatório', 'http://127.0.0.1:8000/lutas/<id>/relatorio/')
bullet(doc, 'Disponível durante e após a luta.')
bullet(doc, 'Exibe placar final com destaque visual do vencedor.')
bullet(doc, 'Estatísticas por atleta: pontos via posição, vantagens, penalizações.')
bullet(doc, 'Linha do tempo completa de todas as ações registradas com horário.')
bullet(doc, 'Suporte a impressão (botão Imprimir).')

# ══════════════════════════════════════════════════════════════════════════════
# 4. TELÃO
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '4. Telão de Placar (Projeção)', 1)
url(doc, 'Telão do tatame', 'http://127.0.0.1:8000/tatame/<id>/placar/')
body(doc,
    'Página pública para projeção em TV ou monitor de grande porte. '
    'Não requer login.')
bullet(doc, 'Placar em tela cheia com fundo escuro de alto contraste.')
bullet(doc, 'Nomes, academias e faixas dos atletas com cores azul (atleta 1) e vermelho (atleta 2).')
bullet(doc, 'Pontos, vantagens e penalizações visíveis para plateia.')
bullet(doc, 'Atualização automática a cada 2 segundos via polling JSON.')
bullet(doc, 'Animação de flash quando o placar muda.')
bullet(doc, 'Relógio em tempo real no canto da tela.')
bullet(doc, 'Quando não há luta em andamento, exibe mensagem de espera.')

# ══════════════════════════════════════════════════════════════════════════════
# 5. MÓDULO DO ATLETA
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '5. Módulo do Atleta', 1)

heading(doc, '5.1 Cadastro e Login', 2)
url(doc, 'Cadastro',  'http://127.0.0.1:8000/atleta/cadastro/')
url(doc, 'Login',     'http://127.0.0.1:8000/atleta/login/')
bullet(doc, 'Cadastro com nome, data de nascimento, faixa, academia, e-mail e foto de documento.')
bullet(doc, 'Ao ser cadastrado, um QR code único é gerado automaticamente para o atleta.')
bullet(doc, 'Login individual com usuário e senha.')

heading(doc, '5.2 Inscrição em Campeonato', 2)
bullet(doc, 'O atleta seleciona o campeonato e a categoria desejada.')
bullet(doc, 'Upload de comprovante de pagamento.')
bullet(doc, 'A inscrição fica com status pendente até aprovação da organização.')
bullet(doc, 'Possibilidade de check-in presencial no dia do evento.')

heading(doc, '5.3 Chaveamento e Resultados', 2)
url(doc, 'Chaveamento', 'http://127.0.0.1:8000/atleta/chaveamento/')
bullet(doc, 'O atleta visualiza sua chave após o chaveamento ser gerado.')
bullet(doc, 'Vê o resultado de cada luta (vencedor, pontuação, tipo de vitória).')
bullet(doc, 'Acompanha tatames em tempo real via página de placar.')

heading(doc, '5.4 Credencial e QR Code', 2)
url(doc, 'Credencial', 'http://127.0.0.1:8000/atleta/credencial/')
bullet(doc, 'Página com dados e QR code para apresentar no credenciamento.')
bullet(doc, 'QR code imprimível para uso no dia do evento.')

# ══════════════════════════════════════════════════════════════════════════════
# 6. MÓDULO DE APOIO / CREDENCIAMENTO
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '6. Módulo de Apoio / Credenciamento', 1)
url(doc, 'Validação', 'http://127.0.0.1:8000/apoio/validar/')
body(doc,
    'Interface para voluntários e equipe de apoio no credenciamento do evento.')
bullet(doc, 'Leitura de QR code do atleta via câmera ou código digitado.')
bullet(doc, 'Exibe foto, faixa, academia e status de inscrição.')
bullet(doc, 'Registra o check-in presencial do atleta.')
bullet(doc, 'Alerta visual se inscrição estiver pendente de aprovação ou pagamento.')

# ══════════════════════════════════════════════════════════════════════════════
# 7. RANKING
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '7. Ranking', 1)
url(doc, 'Ranking', 'http://127.0.0.1:8000/atleta/ranking/')
bullet(doc, 'Classificação geral de atletas por pontos acumulados nos campeonatos.')
bullet(doc, 'Filtro por faixa e categoria.')
bullet(doc, 'Pontuação baseada em vitórias, finalizações e posição no pódio.')

# ══════════════════════════════════════════════════════════════════════════════
# 8. REFERÊNCIA DE URLs
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '8. Referência de URLs', 1)
body(doc, 'Base: http://127.0.0.1:8000  (desenvolvimento local)', italic=True)
doc.add_paragraph()

tabela_acesso(doc,
    [
        ('/organizacao/',                          'Organização',  'Painel principal da organização'),
        ('/organizacao/campeonatos/',              'Organização',  'Gerenciar campeonatos'),
        ('/organizacao/categorias/',               'Organização',  'Gerenciar categorias'),
        ('/organizacao/estrutura/',                'Organização',  'Estrutura / chaveamento'),
        ('/organizacao/tatames-chave/',            'Organização',  'Tatames e distribuição de lutas'),
        ('/organizacao/arbitros/',                 'Organização',  'Gerenciar árbitros'),
        ('/organizacao/mesarios/credenciais/',     'Organização',  'Folha de credenciais imprimível das mesas'),
        ('/mesario/login/',                        'Mesário',      'Login do mesário'),
        ('/mesario/',                              'Mesário',      'Home (tatames vinculados)'),
        ('/mesario/tatame/<id>/',                  'Mesário',      'Mesa de pontuação'),
        ('/arbitro/login/',                        'Árbitro',      'Login do árbitro'),
        ('/arbitro/',                              'Árbitro',      'Home (lista de tatames vinculados)'),
        ('/tatame/<id>/placar/',                   'Público',      'Telão de placar (sem login)'),
        ('/lutas/<id>/relatorio/',                 'Árbitro/Org.', 'Relatório detalhado de luta'),
        ('/atleta/cadastro/',                      'Atleta',       'Cadastro de atleta'),
        ('/atleta/login/',                         'Atleta',       'Login do atleta'),
        ('/atleta/minha-area/',                    'Atleta',       'Área do atleta'),
        ('/atleta/credencial/',                    'Atleta',       'Credencial com QR code'),
        ('/atleta/chaveamento/',                   'Atleta',       'Visualizar chaveamento'),
        ('/atleta/ranking/',                       'Público',      'Ranking geral'),
        ('/apoio/',                                'Apoio',        'Home da equipe de apoio'),
        ('/apoio/validar/',                        'Apoio',        'Validação de QR code / check-in'),
    ],
    ['URL', 'Perfil', 'Descrição']
)

# ══════════════════════════════════════════════════════════════════════════════
# 9. DADOS DE TESTE
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '9. Dados de Teste (Simulação)', 1)
body(doc,
    'O comando simular_campeonato popula o banco com dados fictícios para testes. '
    'Execute antes do primeiro uso:')

p = doc.add_paragraph()
run = p.add_run('python manage.py simular_campeonato --limpar')
run.font.name = 'Courier New'
run.font.size = Pt(10)

body(doc, 'Dados criados pela simulação:', bold=True)
tabela_acesso(doc,
    [
        ('1',  'Campeonato', 'Campeonato Simulado de Jiu-Jitsu 2026'),
        ('8',  'Categorias', 'Branca/Azul × Masculino/Feminino × Leve/Médio/Pesado'),
        ('4',  'Tatames',    'Tatame 1 a Tatame 4'),
        ('4',  'Mesários',   'mesario1 a mesario4 / senha123'),
        ('4',  'Árbitros',   'arbitro1 a arbitro4 / senha123'),
        ('39', 'Atletas',    'atleta1 em diante / senha123'),
        ('36', 'Lutas',      'Resultados simulados em até 3 rodadas (variável por execução)'),
        ('63', 'Técnicas',   'Ações de jiu-jitsu cadastradas em TipoAcao'),
    ],
    ['Qtde', 'Tipo', 'Detalhe']
)

# ══════════════════════════════════════════════════════════════════════════════
# 10. COMANDOS DE GERENCIAMENTO
# ══════════════════════════════════════════════════════════════════════════════
heading(doc, '10. Comandos de Gerenciamento', 1)
body(doc, 'Executados no terminal dentro do diretório do projeto, com o ambiente virtual ativado.')

cmds = [
    ('simular_campeonato',
     'Popula o banco com dados de teste completos.',
     'python manage.py simular_campeonato --limpar'),
    ('seed_acoes',
     'Cadastra as 63 técnicas/ações de jiu-jitsu (TipoAcao).',
     'python manage.py seed_acoes'),
    ('simular_luta_ao_vivo',
     'Simula uma luta ao vivo com ações aleatórias a cada N segundos. '
     'Ideal para testar o telão e a mesa sem árbitro presencial.',
     'python manage.py simular_luta_ao_vivo --tatame 6 --intervalo 2 --max-acoes 20'),
    ('rebalancear tatames (interface)',
     'Na Organização > Estrutura, redistribui as lutas com dois modos: '
     'apenas rodada 1 ou todas as rodadas pendentes; prioriza menor fila e agrupa categorias.',
     'Botões na interface: Rebalancear apenas rodada 1 / Rebalancear todas as rodadas pendentes'),
    ('runserver',
     'Inicia o servidor de desenvolvimento Django.',
     'python manage.py runserver'),
    ('createsuperuser',
     'Cria um superusuário (organização/admin).',
     'python manage.py createsuperuser'),
    ('makemigrations / migrate',
     'Aplica alterações de modelos ao banco de dados.',
     'python manage.py makemigrations\npython manage.py migrate'),
]

for nome, desc, exemplo in cmds:
    heading(doc, nome, 3)
    body(doc, desc)
    p = doc.add_paragraph()
    r = p.add_run(exemplo)
    r.font.name = 'Courier New'
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x1A, 0x5A, 0x96)
    doc.add_paragraph()

# ── Parâmetros do simular_luta_ao_vivo ────────────────────────────────────────
heading(doc, 'Parâmetros do simular_luta_ao_vivo', 3)
tabela_acesso(doc,
    [
        ('--tatame',       '<id>',    'ID do tatame no banco (use o pk exibido no erro se não souber)'),
        ('--intervalo',    '2.0',     'Segundos entre cada ação registrada'),
        ('--max-acoes',    '20',      'Quantidade de ações antes de encerrar por pontos'),
        ('--sem-finalizacao', '—',    'Nunca sorteia finalização; encerra sempre por pontos'),
    ],
    ['Parâmetro', 'Padrão', 'Descrição']
)

# ── Rodapé ────────────────────────────────────────────────────────────────────
doc.add_page_break()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(f'Sistema de Campeonato de Jiu-Jitsu  ·  Manual gerado em {datetime.date.today().strftime("%d/%m/%Y")}')
r.font.size = Pt(9)
set_run_color(r, COR_CINZA)
r.italic = True

# ── Salvar ────────────────────────────────────────────────────────────────────
nome_arquivo = 'Manual_Sistema_Campeonato_JiuJitsu.docx'
doc.save(nome_arquivo)
print(f'Arquivo gerado: {nome_arquivo}')
