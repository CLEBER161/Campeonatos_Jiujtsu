# Sistema de Campeonato de Jiu-Jitsu

Sistema web desenvolvido em Django para gerenciamento completo de campeonatos de jiu-jitsu — inscrições, chaveamento, placar ao vivo, controle de árbitros e mesários.

## Funcionalidades

- **Organização**: criação de campeonatos, categorias automáticas (CBJJ/SJJIF), gestão de estrutura (baias e tatames), controle de árbitros e mesários
- **Chaveamento automático**: geração de chaves por categoria com distribuição inteligente entre tatames
- **Placar ao vivo**: telão por tatame com atualização em tempo real (AJAX polling)
- **Portal do Mesário**: lançamento de pontuação, penalizações e ações de luta
- **Portal do Árbitro**: acompanhamento e sinalização de lutas
- **Inscrição de atletas**: cadastro, inscrição com comprovante de pagamento e geração de QR Code de credencial
- **Check-in**: validação de credenciais por QR Code (portal de apoio)
- **Rebalanceamento de tatames**: redistribuição inteligente de lutas por tatame

## Perfis de acesso

| Perfil | URL |
|---|---|
| Organização | `/organizacao/login/` |
| Mesário | `/mesario/login/` |
| Árbitro | `/arbitro/login/` |
| Atleta | `/atleta/login/` |
| Apoio (check-in) | `/apoio/` |
| Telão tatame | `/tatame/<id>/placar/` |

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/campeonato_jiujitsu.git
cd campeonato_jiujitsu

# 2. Crie o ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate       # Windows
# ou: source .venv/bin/activate  # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
copy .env.example .env         # Windows
# ou: cp .env.example .env       # Linux/Mac
# Edite .env e defina DJANGO_SECRET_KEY

# 5. Aplique as migrações
python manage.py migrate

# 6. Crie o usuário da organização
python manage.py createsuperuser

# 7. (Opcional) Popule com dados de simulação
python manage.py simular_campeonato --limpar

# 8. Rode o servidor
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/organizacao/login/

## Dependências principais

- Django 6.x
- Pillow
- qrcode
- python-docx
- python-dotenv

## Licença

Projeto livre para uso pessoal e educacional.
