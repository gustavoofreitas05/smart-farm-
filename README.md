# 🌱 Smart Farm

**Vídeo de demonstração:** <URL AQUI>

Smart Farm é uma aplicação web para gerenciamento de uma pequena propriedade
rural, combinando operações de gestão (animais, produção, despesas, estoque e
cultivos) com uma camada de processamento de dados (ETL) reservada para dados
ambientais. Foi desenvolvido como projeto final do CS50x.

## Descrição

O projeto nasceu de uma plataforma de dados (extração, transformação e carga
de dados climáticos via API Open-Meteo) e evoluiu para uma aplicação web
completa, com o objetivo de demonstrar, em um único sistema:

- **Desenvolvimento web:** Flask, autenticação de usuários, sessões,
  formulários, templates Jinja, proteção CSRF.
- **Banco de dados:** modelagem relacional em SQLite, chaves estrangeiras,
  queries de agregação para o dashboard.
- **Engenharia de dados:** pipeline de Extract → Transform → Load (pasta
  `src/`), reaproveitado do projeto original de dados climáticos.
- **Visualização de dados:** dashboard com KPIs, indicadores de tendência e
  gráficos (Chart.js).

Cada usuário só enxerga e só consegue alterar os próprios dados: toda tabela
tem uma coluna `user_id`, e toda rota que lê ou grava um registro filtra por
`user_id = <usuário logado>` — inclusive para editar ou excluir, não só para
listar (ver seção "Segurança e autorização").

## Funcionalidades

- **Login e cadastro** de usuários (senha com hash via `werkzeug.security`,
  nunca guardada em texto puro).
- **Dashboard**:
  - KPIs: total de animais, produção dos últimos 7 dias, gastos do mês (com
    indicador de variação percentual em relação ao mês anterior), cultivos
    ativos e itens com estoque baixo.
  - Gráfico de produção diária dos últimos 7 dias.
  - Gráfico de gastos por categoria no mês corrente.
  - Gráfico de tendência de gastos nos últimos 6 meses.
  - Gráfico do que a fazenda mais produziu nos últimos 30 dias, por tipo.
  - Tabela de itens com estoque abaixo do mínimo.
  - Lista de cultivos ativos.
- **Animais**: cadastrar, listar, editar e excluir.
- **Produção**: registrar, editar, excluir e listar produção (ovos, leite,
  colheita etc.), associada opcionalmente a um animal.
- **Despesas**: cadastrar, editar, excluir e listar por categoria (Ração,
  Medicamentos, Manutenção...), com total do período.
- **Estoque**: cadastrar, atualizar quantidade, excluir e receber alerta
  visual quando a quantidade fica abaixo do mínimo definido.
- **Cultivos**: cadastrar, editar, excluir e acompanhar status (ativo,
  colhido, perdido), com data de plantio e previsão de colheita.

Ainda não implementado (próximas fases do roadmap original): integração do
ETL climático diretamente no dashboard, e sensores IoT (ESP32).

## Estrutura do projeto

```
smart-farm/
├── app.py                  # rotas Flask (a "cola" de toda a aplicação)
├── helpers.py               # conexão com o banco, validação, login_required
├── database/
│   └── schema.sql            # schema SQLite (criado automaticamente ao rodar o app)
├── src/                       # pipeline de dados (ETL), independente do Flask
│   ├── extract/
│   ├── transform/
│   └── load/
├── templates/                # HTML (Jinja2)
│   ├── errors/                # páginas de erro 404 / 500
│   ├── animals/ production/ expenses/ inventory/ crops/
├── static/
│   ├── css/style.css
│   └── js/
├── tests/                     # testes automatizados (pytest)
│   ├── conftest.py
│   ├── test_animals.py
│   ├── test_production.py
│   ├── test_expenses.py
│   ├── test_inventory.py
│   └── test_crops.py
└── requirements.txt
```

## Modelo de dados

Todas as tabelas de conteúdo (`animals`, `production`, `expenses`,
`inventory`, `crops`) têm uma chave estrangeira `user_id` para `users(id)`.
`weather_data` já está no schema, reservada para quando o ETL climático for
conectado à aplicação.

```
users ──< animals ──< production
  │
  ├──< expenses
  ├──< inventory
  ├──< crops
  └──< weather_data   (reservada para o ETL)
```

## Decisões de design

- **SQLite** foi escolhido para a versão web (simplicidade, zero
  configuração, ótimo para o escopo do CS50). O ETL original usava
  PostgreSQL; a migração para Postgres é um passo natural se o projeto for
  além do CS50 (múltiplos usuários simultâneos, deploy em produção).
- **Sessões** usam `flask-session` (arquivos em disco), com cookies
  `HttpOnly` e `SameSite=Lax`, e expiração após 8 horas de inatividade.
- **Proteção CSRF** via `Flask-WTF`: toda rota que grava dados (POST) exige
  um token (`csrf_token`) embutido no formulário e validado no servidor —
  sem ele, a requisição é recusada. Isso impede que um site malicioso induza
  o navegador do usuário a enviar ações (como excluir um animal) sem que ele
  perceba.
- **Autorização em toda mutação, não só na listagem**: cada rota de editar ou
  excluir busca o registro com `get_owned_or_404()`, que só retorna a linha
  se ela pertencer ao usuário logado. Se pertencer a outro usuário (ou não
  existir), a rota responde 404 — de propósito, para não revelar se aquele
  id existe na base de outra conta.
- **Validação centralizada** (`helpers.py`): funções como `parse_number`,
  `parse_int` e `parse_date` convertem e validam os campos do formulário,
  levantando `ValidationError` com uma mensagem amigável em português. As
  rotas capturam esse erro e mostram a mensagem via `flash()`, em vez de
  deixar o Flask estourar um erro 500 por causa de um campo de texto onde se
  esperava um número.
- **Páginas de erro próprias** (404/500): em vez da página padrão de debug
  do Flask, o usuário vê uma mensagem no estilo visual da aplicação com um
  link para voltar ao dashboard.
- O **dashboard** calcula os KPIs com queries de agregação (`SUM`,
  `GROUP BY`) diretamente no SQLite, sem processamento em Python, mantendo a
  lógica de negócio próxima dos dados.
- A camada de **ETL** (`src/`) foi mantida separada da aplicação web de
  propósito: ela pode rodar de forma independente (via `cron`/agendador) e
  alimentar as tabelas `weather_data`/`crops` no futuro, sem acoplamento com
  as rotas Flask.

## Segurança — resumo

| Risco | Mitigação |
|---|---|
| Senha em texto puro | Hash com `werkzeug.security.generate_password_hash` |
| Enumeração de usuários no login | Mensagem de erro genérica ("usuário ou senha inválidos") |
| CSRF (ação forjada por outro site) | Token por formulário via Flask-WTF |
| Um usuário acessar/editar dado de outro | Toda query de mutação filtra por `user_id`; `get_owned_or_404` |
| Injeção de SQL | Todas as queries usam parâmetros (`?`), nunca concatenação de strings |
| Entrada inválida quebrando a aplicação | Validação centralizada + páginas de erro 404/500 próprias |
| Roubo de sessão | Cookies `HttpOnly` + `SameSite=Lax`, expiração automática |

**Fora do escopo desta versão** (pontos conhecidos para evolução futura):
não há limite de tentativas de login (rate limiting) nem HTTPS embutido — em
produção, isso ficaria a cargo de um proxy reverso (nginx) e de um serviço
como Flask-Limiter.

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python app.py
```

O banco `database/smart_farm.db` é criado automaticamente na primeira
execução, a partir de `database/schema.sql`.

Acesse `http://127.0.0.1:5000`, crie uma conta e comece a cadastrar seus
dados.

> Em produção, defina a variável de ambiente `SECRET_KEY` com um valor
> aleatório e secreto (`python -c "import secrets; print(secrets.token_hex())"`),
> em vez de usar o valor padrão do código.

## Testes

```bash
pip install -r requirements.txt   # já inclui pytest
pytest tests/ -v
```

A suíte cobre, para cada módulo (animais, produção, despesas, estoque e
cultivos):
- criação e listagem de registros;
- validação de entradas inválidas (número não numérico, data no futuro,
  categoria fora da lista, valor negativo, etc.);
- edição e exclusão;
- isolamento entre usuários (um usuário não consegue editar ou excluir um
  registro de outro usuário — recebe 404).

## Roadmap

1. Conectar o **ETL climático** existente (`src/extract`, `src/transform`,
   `src/load`) ao dashboard, exibindo temperatura/umidade/precipitação.
2. Suporte a sensores (ESP32) alimentando `weather_data` em tempo real.
3. Exportação de relatórios (PDF/CSV) de produção e despesas.
4. Rate limiting no login e HTTPS via proxy reverso, para um deploy real.

## Uso de IA

```
# AI assistance: Claude (Anthropic) foi usado para ajudar a estruturar o
# projeto, gerar o código das rotas Flask, templates, schema do banco de
# dados, validações, testes automatizados e revisar a implementação.
```
