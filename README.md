# 🌱 Smart Farm

**Vídeo de demonstração:**  
<!-- Adicione aqui o link do vídeo antes da submissão -->

## Descrição

O **Smart Farm** é uma aplicação web desenvolvida para facilitar o gerenciamento de uma pequena propriedade rural. O sistema centraliza informações sobre animais, produção, despesas, estoque e cultivos em um único ambiente, permitindo acompanhar os principais dados da propriedade por meio de um dashboard.

O projeto foi desenvolvido como projeto final do **CS50x**, utilizando **Python, Flask, SQLite, Jinja2, Flask-WTF e Chart.js**.

A aplicação possui autenticação de usuários e controle de acesso aos dados. Cada usuário possui seus próprios registros e não consegue visualizar, editar ou excluir dados pertencentes a outra conta.

---

## Funcionalidades

### 🔐 Autenticação

- Cadastro de usuários.
- Login e logout.
- Senhas armazenadas utilizando hash.
- Controle de sessão.
- Proteção das páginas que exigem autenticação.
- Isolamento dos dados entre usuários.

### 📊 Dashboard

O dashboard apresenta um resumo das principais informações da propriedade:

- Quantidade de animais.
- Produção registrada nos últimos 7 dias.
- Despesas do mês atual.
- Comparação das despesas com o mês anterior.
- Quantidade de cultivos ativos.
- Avisos de estoque baixo.
- Gráfico de produção dos últimos 30 dias.
- Gráfico de despesas dos últimos 6 meses.
- Gráfico de produção agrupada por tipo.
- Visualização dos cultivos ativos.

Os gráficos são apresentados utilizando **Chart.js**.

### 🐄 Animais

Permite cadastrar e gerenciar os animais da propriedade.

É possível:

- Adicionar animais.
- Visualizar animais cadastrados.
- Editar registros.
- Excluir registros.
- Informar espécie, nome, sexo e outros dados cadastrados pelo sistema.

### 🥚 Produção

Permite registrar a produção realizada na propriedade.

O sistema possibilita:

- Registrar quantidade produzida.
- Informar o tipo de produção.
- Informar a data da produção.
- Associar uma produção a um animal quando aplicável.
- Editar registros.
- Excluir registros.
- Visualizar a produção registrada no sistema.

Entre os tipos de produção utilizados estão registros como ovos, leite e colheita.

### 💰 Despesas

Permite controlar os gastos da propriedade.

É possível:

- Registrar despesas.
- Informar categoria.
- Informar valor.
- Informar data.
- Editar despesas.
- Excluir despesas.
- Consultar os valores registrados por período.

O dashboard também utiliza esses dados para apresentar informações sobre os gastos da propriedade.

### 📦 Estoque

Permite controlar os itens utilizados na propriedade.

É possível:

- Cadastrar produtos.
- Informar quantidade.
- Informar unidade.
- Definir estoque mínimo.
- Editar produtos.
- Excluir produtos.
- Identificar produtos com estoque baixo.

### 🌱 Cultivos

Permite acompanhar os cultivos existentes na propriedade.

É possível:

- Cadastrar cultivos.
- Informar datas de plantio.
- Informar previsão de colheita.
- Informar status do cultivo.
- Editar registros.
- Excluir registros.

Os cultivos podem possuir diferentes estados, como ativo, colhido ou perdido.

---

## Estrutura do projeto


smart-farm/
├── app.py
├── helpers.py
├── database/
│   └── schema.sql
├── src/
│   ├── extract/
│   ├── transform/
│   └── load/
├── templates/
│   ├── errors/
│   ├── animals/
│   ├── production/
│   ├── expenses/
│   ├── inventory/
│   └── crops/
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
├── tests/
│   ├── conftest.py
│   ├── test_animals.py
│   ├── test_production.py
│   ├── test_expenses.py
│   ├── test_inventory.py
│   └── test_crops.py
├── requirements.txt
└── README.md

A pasta src/ está reservada para futuras integrações relacionadas a dados. Essas estruturas não fazem parte das funcionalidades principais atualmente disponíveis na aplicação.

Banco de dados

O projeto utiliza SQLite como banco de dados.

O schema inicial está localizado em:

database/schema.sql

O banco utilizado pela aplicação é:

database/smart_farm.db

Entre as principais tabelas utilizadas estão:

users
animals
production
expenses
inventory
crops

Existe também uma estrutura weather_data reservada para futuras funcionalidades relacionadas a dados ambientais.

Os registros das entidades principais possuem associação com o usuário responsável, permitindo que cada conta tenha seus próprios dados.

Decisões de projeto
Flask

O Flask foi utilizado como framework principal por permitir desenvolver a aplicação web utilizando Python de maneira simples e modular.

A maior parte das rotas da aplicação está centralizada em:

app.py
SQLite

O SQLite foi escolhido por ser adequado para uma aplicação de pequeno porte e por não exigir um servidor de banco de dados separado para executar o projeto.

Jinja2

Os templates da aplicação utilizam Jinja2, permitindo reutilizar componentes e inserir dados fornecidos pelo Flask nas páginas HTML.

Flask-WTF

O Flask-WTF é utilizado para proteção contra ataques CSRF (Cross-Site Request Forgery).

Validação centralizada

As validações utilizadas pela aplicação foram centralizadas em funções auxiliares presentes em:

helpers.py

Isso evita duplicar regras de validação em diferentes rotas.

Controle de acesso

As operações de edição e exclusão verificam se o registro pertence ao usuário autenticado antes de permitir a operação.

A aplicação utiliza uma função de verificação de propriedade para evitar que um usuário acesse ou altere registros de outra conta.

Dashboard

O dashboard utiliza consultas SQL e agregações para transformar os dados registrados na aplicação em indicadores e gráficos.

Dessa forma, as informações apresentadas são calculadas diretamente a partir dos dados armazenados no banco de dados.

Segurança

A aplicação possui algumas medidas de segurança implementadas:

Recurso	Implementação
Senhas	Armazenadas utilizando hash
Sessões	Controle de sessão do Flask
Cookies	Configurações de segurança aplicadas
CSRF	Proteção utilizando Flask-WTF
Autorização	Verificação de propriedade dos registros
Validação	Validações centralizadas
Erros	Páginas personalizadas para erros 404 e 500

O projeto ainda possui possibilidades de melhorias futuras, como rate limiting e utilização de HTTPS em um ambiente de produção.

Como executar
1. Clonar o repositório
git clone https://github.com/gustavoofreitas05/smart-farm-.git
2. Entrar na pasta do projeto
cd smart-farm-
3. Criar um ambiente virtual

No Linux ou macOS:

python3 -m venv .venv

No Windows:

python -m venv .venv
4. Ativar o ambiente virtual

Linux ou macOS:

source .venv/bin/activate

Windows PowerShell:

.venv\Scripts\Activate.ps1
5. Instalar as dependências
pip install -r requirements.txt
6. Executar a aplicação
python app.py

Depois, abra no navegador:

http://127.0.0.1:5000

O banco de dados é criado a partir do schema localizado em:

database/schema.sql
Testes

O projeto possui testes automatizados utilizando pytest.

Para executar os testes:

pytest tests/ -v

A versão atual do projeto possui 29 testes passando.

Os testes abrangem principalmente as funcionalidades de:

Animais.
Produção.
Despesas.
Estoque.
Cultivos.

Exemplo:

29 passed
Melhorias futuras

Algumas funcionalidades podem ser adicionadas posteriormente ao projeto:

Integração com sensores ambientais.
Integração com ESP32.
Automação de irrigação.
Alimentação automática de animais.
Monitoramento de temperatura e umidade.
Integração de dados meteorológicos.
Exportação de informações para PDF ou CSV.
Melhorias adicionais de segurança para utilização em produção.
Rate limiting.
HTTPS em ambiente de produção.

Essas funcionalidades fazem parte do planejamento futuro e não são necessárias para o funcionamento atual da aplicação.

Uso de Inteligência Artificial

A Inteligência Artificial foi utilizada como ferramenta de apoio durante o desenvolvimento do projeto.

O uso de IA esteve relacionado principalmente a auxílio na estruturação, revisão, identificação de problemas, desenvolvimento e correção de partes do código, além de apoio na documentação e nos testes.

As decisões finais sobre arquitetura, funcionalidades e implementação fazem parte do desenvolvimento do projeto.

Observação: a declaração deve refletir exatamente as ferramentas de IA utilizadas durante o desenvolvimento do projeto.

Autor

Pedro Gustavo Freitas de Souza

GitHub:

https://github.com/gustavoofreitas05/smart-farm-

Licença

Este projeto foi desenvolvido para fins educacionais como parte do CS50x.


**Antes de enviar ao CS50**, só falta substituir:


**Vídeo de demonstração:**  
<!-- Adicione aqui o link do vídeo antes da submissão -->
