# InvControl

Sistema interno de **gerenciamento de inventário** para acompanhar
equipamentos tecnológicos da empresa (computadores, notebooks, monitores,
impressoras, scanners, tablets, trenas digitais, etc.) — quem é
responsável, onde estão, quem cedeu pra quem, e o histórico inteiro do
ciclo de vida de cada peça.

> Aplicação web com backend FastAPI + Postgres e frontend Next.js 16.
> Inteiramente containerizada via Docker Compose. Deploy interno;
> escala confortável para algumas dezenas de usuários simultâneos.

---

## ✨ Principais funcionalidades

- 📦 **Catálogo de equipamentos** com paginação, filtros server-side e
  busca por qualquer campo (nome, série, patrimônio, IP, responsável,
  "sem responsável")
- 🏢 **Centros de Custo (CC)**: organização dos equipamentos por
  contrato/setor, com hierarquia de papéis (Gestor / Subgestor /
  Funcionário)
- 🔄 **Cessões e devoluções** entre CCs com geração automática de
  Termo de Responsabilidade e Termo de Recebimento em PDF; suporta
  **devolução parcial em múltiplos lotes** e **periféricos avulsos**
  (mouse, teclado, kit…) digitados com quantidade — sem patrimônio,
  fora do controle, mas impressos no termo
- ✉️ **Sistema de solicitações** (entrada em CC, mudança de cargo,
  cessão por Subgestor → Gestor)
- 🏷️ **Catálogo dinâmico de tipos** — Admin adiciona/desativa tipos
  (Tablet, Trena Digital…) sem precisar de deploy
- 📍 **Catálogo de localizações** — locais nomeados (Sala TI, Almoxarifado…)
  selecionáveis no form de equipamento; qualquer usuário pode criar nova
  localização inline (Admin gerencia a lista)
- 🏭 **Catálogo de marcas e modelos** — modelo sempre **associado a uma
  marca** (ex.: `OptiPlex 5090 → Dell`); o modelo guarda uma **descrição**
  que é carregada automaticamente na descrição do equipamento quando o
  campo está vazio. Qualquer usuário cria marca/modelo inline no form;
  Admin gerencia as listas (`/marcas`, `/modelos`)
- 🔔 **Notificações** em tempo real para o Gestor quando um
  equipamento é devolvido no CC dele
- 🔒 **Audit log** completo: toda criação, exclusão e mudança crítica
  fica registrada com autor, timestamp e payload
- 📊 **Relatórios** filtráveis e exportáveis em CSV / PDF — agrupamento
  dinâmico por CC, Localização, Responsável, Status, Tipo ou Marca;
  filtros de CC, Localização (pesquisável), Status e Tipo; atalho
  multi-select de Gestor auto-popula os CCs; PDF com cabeçalho
  repetido e indicador "continua na próxima página ↓" em tabelas longas
- 🔐 JWT com refresh transparente, rate-limit no login, headers de
  segurança, hash Argon2 das senhas

---

## 🚀 Quick start

### Pré-requisitos
- Docker + Docker Compose

### Deploy
```bash
git clone <repo>
cd Gerenciamento_de_inventario

# 1. Configure o .env (gere uma SECRET_KEY forte!)
cp .env.example .env
# edite o .env: POSTGRES_PASSWORD, SECRET_KEY, ALLOWED_ORIGINS, etc.

# 2. Suba a stack — alembic upgrade head roda automaticamente
docker compose up -d --build
```

### Portas (configuráveis no `.env`)
| Serviço | Padrão (`.env.example`) | Em uso aqui |
|---|---|---|
| Postgres | `5432` | `5530` |
| Backend | `8000` | `8030` |
| Frontend | `3000` | `3030` |

---

## 👥 Os 5 perfis

Cada usuário tem um **tipo global** (em `User.tipo`) mas a maior parte
das permissões dentro de um CC depende da **ocupação per-CC** —
o mesmo usuário pode ser Gestor em um CC e só Funcionário em outro.

| Perfil | Ícone | Resumo |
|---|---|---|
| **Admin** | 🔴 | Acesso total e irrestrito a tudo |
| **Tecnico_TI** | 🟠 | Foco em equipamentos: total acesso ao inventário e associações, leitura ampla nos outros recursos |
| **Gestor** | 🔵 | Comanda os CCs em que é Gestor (aprova entradas, gerencia membros, cede/devolve equipamentos) |
| **Subgestor** | 🟢 | Como Gestor mas restrito a adicionar/remover apenas Funcionários; cessões viram **solicitações** ao Gestor |
| **Funcionario** | ⚫ | Vê e gerencia só seus próprios equipamentos |

> **Importante**: ocupação per-CC ≠ tipo global. Um usuário com
> `tipo='Gestor'` que é só `Funcionario` no CC X **não** tem
> privilégios de Gestor em X.

---

## 📋 Funcionalidades por cargo

### 🔴 Admin

**Acesso total — pode tudo, em qualquer CC.**

#### Inventário
- ✅ Criar, editar, excluir qualquer equipamento, em qualquer CC
- ✅ Listar todos os equipamentos do sistema
- ✅ Associar/desassociar equipamentos com qualquer usuário

#### Centros de Custo
- ✅ Criar, editar, excluir qualquer CC
- ✅ Adicionar, remover, mudar ocupação de membros em qualquer CC
- ✅ **Único que pode rebaixar/promover Gestores** (Gestor de CC não pode mexer em outro Gestor, mesmo dentro do próprio CC)

#### Cessões
- ✅ Criar cessões com equipamentos de qualquer CC
- ✅ Registrar devolução (total ou parcial) de qualquer cessão
- ✅ **Excluir qualquer cessão** (itens externos voltam pra "Interno")

#### Solicitações
- ✅ Aprovar/rejeitar qualquer solicitação (`entrada_cc`, `cargo_inicial`, `cessao`)
- ✅ **Excluir solicitações em qualquer status** (pendente, aprovada,
  rejeitada) sem restrição

#### Usuários
- ✅ Criar usuários com qualquer tipo via `POST /users/admin`
- ✅ Editar qualquer usuário (incluindo trocar o tipo global)
- ✅ Excluir qualquer usuário

#### Recursos exclusivos do Admin
- 🛠️ **Tipos de Equipamento** (`/tipos`): criar/editar/desativar tipos
  do catálogo (Tablet, Trena Digital, etc.) sem precisar de redeploy
- 📍 **Localizações** (`/localizacoes`): consolidar/editar/excluir a
  lista de locais (Sala TI, Almoxarifado, etc.) — qualquer usuário cria
  inline ao cadastrar equipamento, Admin organiza
- 🏭 **Marcas** (`/marcas`) e **Modelos** (`/modelos`): gerenciar o
  catálogo de fabricantes e seus modelos (cada modelo pertence a uma
  marca e tem descrição própria) — qualquer usuário cria inline ao
  cadastrar equipamento, Admin consolida
- 📜 **Auditoria** (`/auditoria`): histórico de ações críticas com
  filtros por ação, recurso e autor
- 📊 **Relatórios** completos de toda a base
- 🔔 Recebe notificações de **todas** as devoluções do sistema

---

### 🟠 Tecnico_TI

**Equipamentos: acesso total. Outros recursos: leitura ampla.**

#### Inventário
- ✅ Criar, editar, excluir equipamentos em qualquer CC
- ✅ Listar todos
- ✅ Gerenciar associações usuário–equipamento

#### Cessões
- ✅ Criar cessões com qualquer equipamento
- ✅ Registrar devolução de qualquer cessão
- ❌ Não pode excluir cessões (apenas Admin/Gestor envolvido)

#### Centros de Custo
- 👁️ Lista todos os CCs e seus membros (leitura)
- ❌ Não cria, não edita, não remove
- ❌ Não aprova solicitações de entrada

#### Usuários
- 👁️ Lista todos os usuários
- ✅ Edita apenas o **próprio perfil**
- ❌ Não cria nem exclui outros usuários

#### Relatórios
- ✅ Acesso completo aos relatórios

#### Notificações
- 🔔 Recebe **todas** as devoluções do sistema (sem restrição de CC)

---

### 🔵 Gestor

**Comanda os CCs em que tem ocupação `Gestor`.**

#### Nos CCs em que é Gestor
- ✅ **Editar e excluir** o CC
- ✅ Adicionar, remover membros
- ✅ Promover Funcionário/Subgestor → outro cargo
- ❌ **Não pode mexer no cargo de outro Gestor** (mesmo no próprio CC) — só Admin faz isso
- ✅ Aprovar/rejeitar solicitações de entrada (`entrada_cc`)
- ✅ Aprovar/rejeitar solicitações de cessão de Subgestores
  (`solicitacao.cessao`)
- ✅ Convidar usuários via `POST /solicitacoes/convite-cc`
- ✅ Gerenciar equipamentos (criar, editar, excluir, associar a qualquer membro)
- ✅ **Criar cessões** com equipamentos do CC
- ✅ Registrar devoluções
- ✅ **Excluir cessões** envolvendo seu CC
- 🔔 Recebe notificações de devoluções no(s) CC(s) dele

#### Em outros CCs
- 👁️ Pode listar os CCs (precisa pra solicitar entrada em outros)
- ❌ Sem privilégios especiais

#### Relatórios
- ✅ Acesso aos relatórios (limitado aos seus CCs se não for Admin/TI)

#### Solicitações
- ✅ Pode pedir entrada em outros CCs com qualquer cargo
- ✅ Pode pedir upgrade pra outro tipo global (`cargo_inicial`) — só Admin aprova

---

### 🟢 Subgestor

**Como Gestor, mas restrito a Funcionários no CC.**

#### Nos CCs em que é Subgestor
- ✅ Adicionar **apenas Funcionários** ao CC
- ✅ Remover **apenas Funcionários** do CC
- ✅ Aprovar/rejeitar solicitações de entrada **com cargo Funcionário**
- ❌ Não pode promover ninguém a Gestor/Subgestor
- ❌ Não pode editar nem excluir o CC
- ✅ Gerenciar equipamentos do CC (criar, editar, associar)
- ⚠️ **Não pode criar cessão diretamente** — envia
  `solicitacao.cessao` ao Gestor; o Gestor aprova → cessão real é criada
- ✅ Registrar devolução de cessões existentes
- ❌ Não pode excluir cessões

#### Em outros CCs
- 👁️ Lista os CCs
- ✅ Pode solicitar entrada em outros

#### Relatórios
- ✅ Acesso aos relatórios dos seus CCs

---

### ⚫ Funcionário

**Vê e gerencia apenas o que é dele.**

#### Inventário
- 👁️ Lista **apenas os equipamentos associados a ele** (mesmo no CC dele)
- ✅ Criar novos equipamentos no CC dele (são **auto-associados** a ele)
- ✅ Editar/excluir **apenas os próprios**

#### Centros de Custo
- 👁️ Lista todos os CCs (necessário pra poder solicitar entrada)
- ✅ Pode pedir **entrada em outro CC** via solicitação
- ✅ Pode **sair do próprio CC** (self-removal, exceto se for único
  Gestor — caso impossível pra Funcionário, mas a regra vale)

#### Cessões
- ❌ Não cria, não exclui
- ✅ Pode **registrar devolução** de qualquer cessão envolvendo seu CC
  (qualquer membro do CC pode receber o equipamento de volta —
  fica registrado quem foi no termo de recebimento)

#### Solicitações
- ✅ Cria solicitação de entrada em CCs
- ✅ Cria solicitação de upgrade de cargo (`cargo_inicial`)
- ✅ Cancela apenas as **próprias solicitações pendentes**

#### Usuários
- 👁️ Lista apenas usuários **do mesmo CC**
- ✅ Edita apenas o **próprio perfil** (nome, email, senha)

---

## 🔔 Notificações em tempo real (polling 5s)

| Quem | O quê vê |
|---|---|
| Qualquer perfil | Badge na sidebar com solicitações pendentes |
| Convidado | Sino na topbar quando recebe convite pra CC |
| **Gestor** | Badge "Cessões" quando alguém devolve equipamento em CC dele |
| **Admin / Tecnico_TI** | Badge "Cessões" para **todas** as devoluções do sistema |

---

## 🏗️ Arquitetura (alto nível)

```
┌──────────────────┐         ┌──────────────────┐         ┌─────────────┐
│  Browser         │ HTTPS   │  Next.js 16      │  HTTP   │  FastAPI    │
│  Frontend SPA    ├────────▶│  (proxy reverso) ├────────▶│  Backend    │
│  Port 3030       │         │  + páginas SSR   │         │  Port 8030  │
└──────────────────┘         └──────────────────┘         └──────┬──────┘
                                                                  │ asyncpg
                                                                  ▼
                                                          ┌─────────────┐
                                                          │ PostgreSQL  │
                                                          │ Port 5530   │
                                                          └─────────────┘
```

**Camadas no backend**: `Routers → Services → Models`. Cada rota
injeta um `UserContext` (usuário + ocupações por CC) e a autorização
é feita no service.

**Proxy do frontend**: `/api/*` no Next.js encaminha pro backend
internamente — o browser nunca conhece o host do backend.

Detalhes em [backend/README.md](backend/README.md) e
[frontend/frontend/README.md](frontend/frontend/README.md).

---

## 🛠️ Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2 (async), Pydantic v2, Alembic, PyJWT, pwdlib (Argon2), slowapi |
| Banco | PostgreSQL 16 (asyncpg) |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, shadcn/ui, next-themes, sonner |
| Infra | Docker + Docker Compose |
| Qualidade | Ruff (lint + format), pytest + pytest-asyncio + factory-boy (97% coverage), ESLint, TypeScript strict |

---

## 📚 Documentação técnica

- [backend/README.md](backend/README.md) — endpoints, modelo de autorização per-CC, migrations, testes
- [frontend/frontend/README.md](frontend/frontend/README.md) — estrutura de páginas, API client, proxy, theming
---

## 📜 Regras de negócio detalhadas

### Cadastro de usuários

- **Auto-registro público** (`POST /users/`) sempre cria
  `tipo='Funcionario'`, mesmo que o cliente envie outro valor.
- O auto-registro pode ser restrito a domínios específicos via
  `ALLOWED_EMAIL_DOMAINS` no `.env` (ex.: só aceita
  `@ufcengenharia.com.br` ou `@sememail.com`).
- Senha mínima de **8 caracteres** (validado no backend e no frontend).
- Para cargos acima de Funcionário, o usuário envia
  `solicitacao.cargo_inicial` — só Admin aprova.

### Catálogo de marcas e modelos

- **Marca** (`tb_marcas`): só nome (único) — a descrição **não** fica na
  marca.
- **Modelo** (`tb_modelos`): nome + **descrição** + `marca_id` (FK com
  `ON DELETE CASCADE`). O nome do modelo é único **por marca**, então o
  mesmo nome pode existir em marcas diferentes.
- `Eletronico.marca` e `Eletronico.modelo` continuam como **texto** — a
  ligação com o catálogo é por nome (mesmo padrão de localizações/tipos),
  com rename em cascata quando o Admin renomeia uma marca/modelo.
- No form de equipamento, o select de modelo é **filtrado pela marca**
  escolhida; criar/escolher um modelo carrega a descrição dele na
  descrição do equipamento **apenas se o campo estiver vazio** (não
  sobrescreve peculiaridades já digitadas). O botão **"Carregar descrição
  do modelo"** força a sobrescrita, com confirmação.
- Qualquer usuário autenticado pode criar marca/modelo; só Admin
  edita/exclui (`/marcas`, `/modelos`).

### Renomear o código do Centro de Custo

- O código do CC (PK de 4 caracteres) pode ser **editado** por Admin ou
  Gestor do CC (botão de editar no card em `/centros-de-custo`).
- A mudança **propaga em cascata** para tudo que referencia o CC:
  equipamentos, associações usuário-CC, cessões e solicitações. No banco,
  os FKs usam `ON UPDATE CASCADE`; o service também atualiza as colunas
  que não são FK (destino de cessões/solicitações).
- Renomear para um código já existente retorna 409.

### Periféricos avulsos na cessão

- Ao ceder, é possível **digitar periféricos** (mouse, teclado, kit
  teclado+mouse…) com **quantidade**. Não têm patrimônio e **não entram
  no controle de inventário** — existem só para constar no **Termo de
  Responsabilidade**.
- Funciona tanto no fluxo direto (Admin/TI/Gestor) quanto na
  **solicitação** do Subgestor: os periféricos viajam na solicitação e
  são **copiados para a cessão real** na aprovação do Gestor.

### Cessões com devolução parcial

- Uma cessão pode ter múltiplos lotes de devolução.
- Cada lote gera seu próprio Termo de Recebimento numerado
  (`#1`, `#2`, …).
- Quando todos os equipamentos retornam, o status muda automaticamente
  para `devolvida`.
- **Qualquer membro do CC** (de qualquer ocupação) pode registrar a
  devolução. Quem registrou fica gravado em `devolvida_por_id` e
  aparece no termo.

### Solicitação de cessão (Subgestor → Gestor)

1. Subgestor seleciona equipamentos do seu CC + responsável + CC destino
2. Sistema cria `Solicitacao(tipo='cessao')`
3. Gestor do CC origem vê a solicitação em `/solicitacoes` com link
   pra "ver termo" (proposta)
4. Gestor aprova → `Cessao` real é criada automaticamente; itens
   marcados como `Externo`
5. Gestor rejeita → nada acontece com os itens

### Audit log

Eventos registrados em `tb_audit_log`:

- `cessao.create`, `cessao.devolver`, `cessao.delete`
- `solicitacao.aprovar`, `solicitacao.rejeitar`, `solicitacao.cancelar`,
  `solicitacao.delete`
- `user.delete`, `user.tipo_change`
- `contrato.create`, `contrato.update`, `contrato.delete`
- `cc.membro.add`, `cc.membro.ocupacao_change`, `cc.membro.remove`,
  `cc.membro.self_remove`

Cada entry tem `user_id` (quem fez), `target_type`, `target_id`,
`payload` (snapshot dos campos relevantes) e `criado_em`. Acesso à
visualização em `/auditoria` é restrito ao Admin.

---

## 🔐 Segurança

- JWT assinado com HS256, TTL configurável (`ACCESS_TOKEN_EXPIRE_MINUTES`,
  default 60 min)
- Senhas com hash **Argon2id** via pwdlib
- Rate limit no login (default `10/minute`) — configurável via
  `LOGIN_RATE_LIMIT`
- CORS apertado (`ALLOWED_ORIGINS` no `.env`)
- Headers de segurança: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`
- GZip middleware no backend
- `.env` no `.gitignore` (use `.env.example` como referência)

---

## 🧪 Testes

```bash
cd backend
task test
```

254 testes (inclui CRUD de marcas/modelos, rename de CC com propagação
e periféricos de cessão). Suíte usa SQLite em memória via override de
dependência.

---

## 📦 Migração

```bash
# Migrations (rola automático no entrypoint do container)
docker compose exec backend alembic upgrade head

# Status
docker compose exec backend alembic current

```
