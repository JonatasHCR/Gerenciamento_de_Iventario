# InvControl — Backend

API FastAPI para o sistema de gerenciamento de inventário InvControl.

**Stack:** Python 3.13 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL (asyncpg) · Alembic · Pydantic v2 · PyJWT · pwdlib (Argon2) · slowapi · Poetry · Ruff · Pytest

## Setup local

```bash
cd backend
poetry install
cp .env.example .env       # ajuste DB_USER, DB_PASSWORD, SECRET_KEY, etc.
alembic upgrade head       # cria todas as tabelas + seed dos 5 tipos
task run                   # fastapi dev backend/app.py → http://localhost:8000
```

Em Docker (recomendado): tudo é orquestrado pelo `docker-compose.yml` na raiz do repo. O entrypoint do container já roda `alembic upgrade head && fastapi run`.

Documentação interativa em `http://localhost:8000/docs`.

## Variáveis de ambiente

| Var | Default | Descrição |
|---|---|---|
| `ENGINE_ASYNC` | `postgresql+asyncpg` | Driver SQLAlchemy async |
| `ENGINE_SYNC` | `postgresql+psycopg2` | Não usado em runtime (Alembic é async) |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | — | Conexão Postgres |
| `SECRET_KEY` | obrigatório | Chave HS256 do JWT (gere com `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | TTL do access token. Frontend renova via `/auth/refresh_token` automaticamente em 401. |
| `DEBUG` | `false` | `true` ativa `echo` no SQLAlchemy (loga toda query). **Nunca true em produção.** |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Origens permitidas no CORS, separadas por vírgula |
| `LOGIN_RATE_LIMIT` | `10/minute` | Rate limit no `/auth/login` (formato slowapi) |
| `ALLOWED_EMAIL_DOMAINS` | vazio | Domínios permitidos no auto-registro público (`POST /users/`). Vazio = qualquer domínio. Ex.: `ufcengenharia.com.br,sememail.com` |

## Estrutura

```
backend/
├── backend/
│   ├── app.py                  # FastAPI + middlewares (CORS, GZip, security headers)
│   ├── bootstrap_admin.py      # Script one-shot pra criar o 1º Admin (apagar após uso)
│   ├── core/
│   │   ├── database.py         # Base declarativa
│   │   ├── engine.py           # AsyncEngine + SessionLocal
│   │   ├── limiter.py          # slowapi Limiter compartilhado
│   │   ├── pagination.py       # helper paginate(session, query, page, page_size)
│   │   └── settings.py         # Pydantic Settings (.env)
│   ├── model/                  # SQLAlchemy ORM
│   │   ├── audit_log.py        # tb_audit_log
│   │   ├── tipo_eletronico.py  # tb_tipos_eletronico (catálogo dinâmico)
│   │   ├── localizacao.py      # tb_localizacoes (catálogo dinâmico)
│   │   ├── marca.py            # tb_marcas (catálogo)
│   │   ├── modelo.py           # tb_modelos (catálogo, FK → tb_marcas)
│   │   └── ... (user, contrato, eletronico, cessao, solicitacao, associações)
│   ├── schemas/                # Pydantic v2 (Create, Update, Read, List)
│   ├── routers/                # Handlers HTTP finos
│   ├── service/                # Regras de negócio + permissões
│   └── security/               # JWT, hash Argon2, UserContext, dependências
├── migrations/                 # Alembic (env.py async, 1 única migration inicial)
├── tests/                      # Pytest (97% coverage)
└── pyproject.toml              # Poetry + Ruff + Taskipy
```

## Comandos (via `task`)

```bash
task run        # fastapi dev backend/app.py
task lint       # ruff check
task format     # ruff check --fix && ruff format
task test       # pytest -s -x --cov=backend -vv (+ coverage html)
```

## Migrations

O esquema parte de uma migration inicial consolidada (`8b33ec3fe9f3_initial_schema.py`) que cria as tabelas base, índices, constraints e seed dos 5 tipos default. Migrations posteriores adicionam recursos incrementais, entre elas:

- `a1f8c4d9b372` — `tb_localizacoes`
- `b5c9e2f1a8d3` — `tb_marcas` e `tb_modelos`
- `c7d1a3e9f2b4` — backfill de marcas/modelos a partir de `tb_eletronicos`
- `d9f2b6c1a4e7` — backfill da descrição dos modelos (descrição mais recente por marca+modelo)
- `e3a7c8d2f5b9` — `ON UPDATE CASCADE` no FK `centro_custo` das solicitações (habilita rename do CC)
- `f1b8d4e6a9c2` — `tb_cessao_periferico` (periféricos avulsos da cessão)
- `a2c5e8b1d4f7` — `tb_modelos.descricao` para `TEXT` (multilinha)
- `b6e9c3f2a8d1` — `tb_solicitacao_periferico` (periféricos da solicitação de cessão)

```bash
alembic revision --autogenerate -m "descrição"   # gera nova migration
alembic upgrade head                              # aplica pendentes
alembic downgrade -1                              # reverte uma
alembic current                                   # mostra revisão atual
```

> ⚠️ Alembic **não** detecta `CheckConstraint`. Escreva-os manualmente via `op.create_check_constraint()` / `op.drop_constraint(..., type_='check')`.

## Arquitetura

App em camadas: **Routers → Services → Models**. Routers são handlers HTTP finos; toda lógica de negócio fica em `service/`. Cada service recebe um `UserContext` (em `security/dependencies.py`) que encapsula:

```python
@dataclass
class UserContext:
    user: User
    centros_custo: list[str]
    ocupacoes: dict[str, str]   # { centro_custo: ocupacao }
    is_privileged: bool          # True só para Admin
    is_tecnico_ti: bool
```

Use `ctx.assert_cc(cc)`, `ctx.assert_write(*tipos)` e `ctx.assert_cc_role(cc, *roles)` para enforcement de permissões. Admin sempre bypassa em `assert_cc_role`; nenhum bypassa para `Tecnico_TI`.

### Hierarquia de papéis (`User.tipo`)

| Papel | Capabilities |
|---|---|
| `Admin` | Acesso total. Único que pode acessar `/audit-log/` e `/tipos-eletronico/` (escrita). |
| `Tecnico_TI` | Total em eletrônicos/associações de eletrônicos; leitura ampla; sem aprovar/rejeitar solicitações |
| `Gestor` | Gerencia CCs em que tem ocupação `Gestor`: aprova entradas, convida, cria/exclui cessões |
| `Subgestor` | Como Gestor mas restrito a `Funcionario`; cessões viram solicitações ao Gestor |
| `Funcionario` | Vê só seu CC e os eletrônicos a ele associados |

## Middlewares e segurança

Em `app.py`:

- **CORS** — origens vêm de `ALLOWED_ORIGINS` (env).
- **GZip** — compressão automática para responses ≥ 1 KB.
- **Security headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy`.
- **Rate limit (slowapi)** — `/auth/login` limitado por IP via `LOGIN_RATE_LIMIT`. Limiter compartilhado em `core/limiter.py`; em testes basta `limiter.enabled = False`.

Outras proteções:
- Hash de senha com **Argon2id** via pwdlib.
- `POST /users/` (auto-registro) força `tipo='Funcionario'` e valida domínio do email contra `ALLOWED_EMAIL_DOMAINS` se configurado.
- Senha mínima de 8 caracteres no `UserCreate` e `UserUpdate.senha`.

## Solicitações (`/solicitacoes`)

Três tipos (`Solicitacao.tipo`):

**`entrada_cc`** — entrar num CC
- `POST /solicitacoes/entrada-cc` (qualquer autenticado)
- `POST /solicitacoes/convite-cc` (Gestor/Subgestor convida usuário — define `convidado_por_id`)
- Aprovar: sem convite → Gestor/Subgestor do CC ou Admin. Com convite → o próprio convidado ou Admin.

**`cargo_inicial`** — upgrade de tipo acima de Funcionario
- `POST /solicitacoes/cargo-inicial` — `cargo_solicitado ∈ {Gestor, Subgestor, Tecnico_TI}`
- Aprovar: somente Admin.

**`cessao`** — Subgestor solicita cessão ao Gestor do CC
- `POST /solicitacoes/cessao` — payload `{ eletronico_ids, responsavel, centro_custo_destino, perifericos? }`
- Solicitante deve ser **Subgestor** do CC dos itens; todos os itens devem ser do **mesmo CC de origem** e estarem `Interno`.
- Periféricos avulsos opcionais (`tb_solicitacao_periferico`) viajam na solicitação e são **copiados para a `Cessao` real** na aprovação.
- Aprovar: Admin OU Gestor do CC de origem → cria a `Cessao` automaticamente e marca itens como `Externo`.

Visibilidade no GET:
- Admin → todas
- Gestor → suas CCs (entrada + cessão) + as próprias
- Subgestor → suas CCs (só `entrada_cc` de `Funcionario`) + as próprias
- Demais → apenas as próprias

### Exclusão (`DELETE /solicitacoes/{id}`)

- **Admin**: apaga qualquer solicitação, em **qualquer status** (`pendente`, `aprovada`, `rejeitada`), sem restrição de CC.
- Solicitante: cancela apenas as próprias `pendente`.
- Demais: 403.

## Autorização **per-CC** (ocupação, não tipo global)

**Regra crítica:** permissões em recursos de um CC dependem da `ocupacao` do usuário **naquele CC** (em `tb_associacao_user_contrato`), não do `User.tipo` global.

| Recurso | Operação | Autorização per-CC |
|---|---|---|
| `Contrato` | update/delete do CC X | Admin OU ocupação = `Gestor` em X |
| `Contrato` | rename do código (PK) | Admin OU `Gestor` em X — propaga p/ eletrônicos, associações, cessões e solicitações (FK `ON UPDATE CASCADE` + updates no service) |
| `Eletronico` | create no CC X | Admin/TI OU ocupação ∈ {Gestor, Subgestor, Funcionario} em X (Funcionario → auto-associa a si mesmo) |
| `Eletronico` | update/delete | Admin/TI OU ocupação Gestor/Subgestor no CC do eletrônico OU (Funcionario no CC + dono via associação) |
| `AssociacaoUserContrato` | create/delete | Admin OU ocupação Gestor no CC (Subgestor pode criar/remover só `Funcionario`); self-removal permitido |
| `AssociacaoUserContrato` | update (mudar cargo) | Admin OU ocupação Gestor no CC — porém **Gestor não pode alterar o cargo de outro Gestor** (apenas Admin) |
| `AssociacaoUserEletronico` | create/delete | Admin/TI OU Gestor/Subgestor no CC do eletrônico OU (Funcionario no CC + sua própria associação) |
| `Cessao` | create | Admin/TI OU Gestor de algum CC envolvido |
| `Cessao` | devolver | Admin/TI OU qualquer ocupação em algum CC envolvido |
| `Cessao` | delete | Admin OU Gestor de algum CC envolvido |

**Implementação:** `UserContext.assert_cc_role(cc, *roles)` em `security/dependencies.py`. Admin sempre bypassa. Tecnico_TI **não** bypassa nesse helper — quem chama decide explicitamente.

Métodos auxiliares: `ctx.ocupacao_in(cc)` retorna a string da ocupação ou None.

**Implicação importante:** um usuário com `tipo='Gestor'` (global) que é só `Funcionario` no CC X **não tem** privilégios de Gestor em X. Inversamente, um `Funcionario` (global) que é Gestor em CC Y tem privilégios completos de Gestor em Y.

## Visibilidade e self-removal de CCs

- `GET /contratos/`: **todos os usuários autenticados veem todos os CCs**. Necessário pra Funcionário/Subgestor/Gestor descobrirem outros CCs e solicitarem entrada. Permissões de write (create/update/delete) continuam restritas a Gestor/Admin do próprio CC.
- `DELETE /associacoes/contratos/{user_id}/{cc}`: permite **self-removal** (qualquer usuário sai do CC se `user_id == ctx.user.id`). Em ambos os casos, **bloqueia 409** se o usuário a ser removido é o único `Gestor` do CC.

## Paginação e filtros (`GET /eletronicos/`)

Filtros server-side + paginação:

**Query params:**
| Param | Tipo | Descrição |
|---|---|---|
| `q` | string | Texto da busca (interpretação depende do `campo`) |
| `campo` | enum | Campo de busca: `todos` (default), `nome`, `numero_serie`, `numero_patrimonio`, `marca`, `modelo`, `ip`, `localizacao`, `responsavel`, `sem_responsavel` |
| `centro_custo` | list[str] | Filtra por CCs (`?centro_custo=A&centro_custo=B`) |
| `status` | list[str] | `Interno`, `Externo`, `Em Manutenção` |
| `tipo` | list[str] | Filtra por tipo (cf. `tb_tipos_eletronico`) |
| `page` | int ≥1 | Default 1 |
| `page_size` | int 1–1000 | Default 50 |

Filtro especial `campo=responsavel` faz join via `AssociacaoUserEletronico → User.nome` com ILIKE em `q`. `campo=sem_responsavel` ignora `q` e retorna só equipamentos sem nenhuma associação.

**Resposta:**
```json
{
  "eletronicos": [...],
  "total": 123,
  "page": 1,
  "page_size": 50,
  "pages": 3
}
```

As regras de visibilidade por papel (Admin/TI vê tudo, Gestor/Subgestor só seus CCs, Funcionario só os seus) continuam aplicadas **antes** dos filtros, em `EletronicoService._base_query()`.

**Helper de paginação** em `backend/core/pagination.py`.

## Cessões de equipamentos (`/cessoes`)

Histórico persistido de cessões com suporte a **devolução parcial em múltiplos lotes**.

**Modelo:**
- `Cessao`: `responsavel`, `centro_custo_destino`, `cedido_em`, `cedido_por_id`, `devolvida_em`, `devolvida_por_id` (preenchidos quando o último item retorna).
- `CessaoEletronico` (N:N): cada linha carrega `devolvido_em`, `devolvida_por_id`, `devolucao_lote` (1, 2, 3… sequencial por cessão) e `gestor_visto_em`.
- `CessaoPeriferico` (`tb_cessao_periferico`): periféricos avulsos (`nome`, `quantidade`) digitados na cessão — **sem patrimônio, fora do controle de inventário**, só constam no Termo. Aceitos no `POST /cessoes/` via `perifericos: [{nome, quantidade}]` e retornados em `CessaoRead.perifericos`.
- Status derivado: `ativa` (zero devolvidos), `parcial` (alguns), `devolvida` (todos).

**Endpoints:**

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/cessoes/` | Lista cessões visíveis com `eletronicos[]`, `devolucoes[]` agrupadas por lote, `status`, contagens |
| `GET` | `/cessoes/{id}` | Detalhes da cessão |
| `POST` | `/cessoes/` | Cria cessão — marca itens como `Externo` |
| `PUT` | `/cessoes/{id}/devolver` | Devolve **alguns** ou todos os itens: `{ eletronico_ids, devolvida_em? }` |
| `DELETE` | `/cessoes/{id}` | Apaga a cessão. Itens externos voltam para `Interno`. |
| `GET` | `/cessoes/recebimentos/pendentes-gestor` | Lista lotes ainda não vistos (notificação) |
| `PUT` | `/cessoes/recebimentos/visto` | Marca todos os pendentes como vistos |

### Notificações de recebimento

Sempre que uma devolução é registrada, fica com `gestor_visto_em IS NULL`.

| Papel | Vê quais devoluções pendentes |
|---|---|
| **Admin** | **Todas**, sem restrição de CC |
| **Tecnico_TI** | **Todas**, sem restrição de CC |
| **Gestor** | Apenas dos CCs onde tem `ocupacao = 'Gestor'` |
| Demais | Nenhuma (endpoint retorna `count: 0`) |

Estado de "visto" é **compartilhado** entre supervisores — quando qualquer Admin/TI/Gestor abre `/cessoes`, todos os pendentes em escopo são marcados como vistos.

## Catálogo dinâmico de tipos (`/tipos-eletronico/`)

`Eletronico.tipo` é validado contra o catálogo dinâmico `tb_tipos_eletronico` (não mais via `CheckConstraint`). O Admin pode adicionar/desativar tipos sem deploy.

**Endpoints:**

| Método | Rota | Quem |
|---|---|---|
| `GET` | `/tipos-eletronico/?apenas_ativos=true` | Qualquer autenticado |
| `POST` | `/tipos-eletronico/` | Admin |
| `PUT` | `/tipos-eletronico/{id}` | Admin (rename faz **cascade** nos `tb_eletronicos.tipo` via UPDATE) |
| `DELETE` | `/tipos-eletronico/{id}` | Admin (soft-delete se houver equipamento usando) |

Service `TipoEletronicoService.assert_nome_valido(nome)` é chamado em `EletronicoService.create/update` — falha 422 se tipo não existe ou está desativado.

Seed inicial (na migration): `Computador`, `Notbook`, `Monitor`, `Impressora`, `Scanner`.

## Catálogo de localizações (`/localizacoes/`)

Catálogo de locais nomeados (Sala TI, Almoxarifado, Sala da Diretoria…) — armazenado em `tb_localizacoes` e referenciado por nome (string) em `Eletronico.localizacao`.

**Endpoints:**

| Método | Rota | Quem |
|---|---|---|
| `GET` | `/localizacoes/` | Qualquer autenticado |
| `POST` | `/localizacoes/` | **Qualquer autenticado** (criar inline ao cadastrar equipamento) |
| `PUT` | `/localizacoes/{id}` | Admin (rename faz cascade em `tb_eletronicos.localizacao`) |
| `DELETE` | `/localizacoes/{id}` | Admin |

Diferentemente do catálogo de tipos (`/tipos-eletronico/`), aqui qualquer usuário pode adicionar — a ideia é que durante o cadastro de equipamento se o local não estiver na lista, o usuário cria inline.

Sem CHECK constraint no `Eletronico.localizacao` — a validação é "soft": o frontend apenas usa o catálogo pra autocompletar/manter consistência. O backend aceita qualquer string (mantendo retrocompatibilidade).

## Catálogo de marcas e modelos (`/marcas/`, `/modelos/`)

Catálogo de fabricantes (`tb_marcas`) e seus modelos (`tb_modelos`), no mesmo padrão "soft" das localizações: `Eletronico.marca` e `Eletronico.modelo` continuam **strings**, referenciadas por nome, com rename em cascata.

**Modelos:**
- `Marca`: `id`, `nome` (único), `criado_em`. **Sem descrição** — a descrição é do modelo.
- `Modelo`: `id`, `nome`, `descricao`, `marca_id` (FK → `tb_marcas`, `ON DELETE CASCADE`), `criado_em`. Unique `(marca_id, nome)` — o mesmo nome de modelo pode existir em marcas diferentes. `ModeloRead` expõe `marca_nome` (via relationship).

**Endpoints — `/marcas/`:**

| Método | Rota | Quem |
|---|---|---|
| `GET` | `/marcas/` | Qualquer autenticado |
| `POST` | `/marcas/` | **Qualquer autenticado** (criar inline ao cadastrar equipamento) |
| `PUT` | `/marcas/{id}` | Admin (rename faz cascade em `tb_eletronicos.marca`) |
| `DELETE` | `/marcas/{id}` | Admin (remove os modelos da marca via FK CASCADE) |

**Endpoints — `/modelos/`:**

| Método | Rota | Quem |
|---|---|---|
| `GET` | `/modelos/?marca_id={id}` | Qualquer autenticado (filtro opcional por marca) |
| `POST` | `/modelos/` | **Qualquer autenticado** — exige `marca_id` válido (422 se não existir) |
| `PUT` | `/modelos/{id}` | Admin (rename faz cascade em `tb_eletronicos.modelo`) |
| `DELETE` | `/modelos/{id}` | Admin |

No frontend, o select de modelo é filtrado pela marca escolhida; selecionar/criar um modelo carrega a descrição dele na descrição do equipamento **só se o campo estiver vazio** (botão "Carregar descrição do modelo" força a sobrescrita).

## Audit log (`/audit-log/`)

Tabela append-only `tb_audit_log` registra ações críticas:

| Action | Quando |
|---|---|
| `cessao.create`, `cessao.devolver`, `cessao.delete` | CRUD de cessões |
| `solicitacao.aprovar`, `.rejeitar`, `.cancelar`, `.delete` | Decisões em solicitações (`.delete` = Admin apaga qualquer status) |
| `user.delete`, `user.tipo_change` | Ações em usuários |
| `contrato.create`, `.update`, `.delete` | CRUD de CCs |
| `cc.membro.add`, `.ocupacao_change`, `.remove`, `.self_remove` | Mudanças em membros de CC |

Cada entry: `action`, `user_id` (quem fez), `target_type`, `target_id`, `payload` (JSON com snapshot), `criado_em`.

`GET /audit-log/?action=...&target_type=...&user_id=...&page=...&page_size=...` — paginado, **somente Admin** (Tecnico_TI e demais recebem 403).

Helper: `service/audit_log.py:log(session, action, user_id, target_type, target_id, payload)` — adiciona à sessão sem commitar (o caller commita; rollback descarta o log junto).

## Validações no model

- `Eletronico.tipo` — validado contra `tb_tipos_eletronico` (não há CHECK constraint; soft-validation no service)
- `Eletronico.marca` / `Eletronico.modelo` — strings referenciando os catálogos `tb_marcas` / `tb_modelos` por nome (soft, sem CHECK; rename em cascata)
- `Eletronico.status IN ('Interno', 'Externo', 'Em Manutenção')` — `check_status_valid`
- `Eletronico.centro_custo` FK para `tb_contratos.centro_custo` (CASCADE)
- `Contrato.centro_custo` — `VARCHAR(4)` no DB; Pydantic `ContratoCreate` valida `max_length=4` (retorna 422 antes de chegar ao banco, evitando `StringDataRightTruncationError`)
- `User.tipo IN ('Admin', 'Funcionario', 'Gestor', 'Subgestor', 'Tecnico_TI')` — `check_tipo_valid`
- `Solicitacao.tipo IN ('entrada_cc', 'cargo_inicial', 'cessao')` — `check_solicitacao_tipo`
- `Solicitacao.status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada')` — `check_solicitacao_status`

## Testes

```bash
task test                                                  # tudo (lint + pytest + coverage html)
pytest tests/routers_tests/test_router_users.py -s -x -vv  # arquivo único
pytest -k "test_create_user" -vv                           # filtro por nome
```

**254 testes** (inclui CRUD de marcas/modelos, rename de CC com
propagação e periféricos de cessão/solicitação).

Tests usam SQLite (`aiosqlite`) em memória via override do `EngineApp.get_async_session`. O conftest faz seed automático dos 5 tipos default + desabilita rate-limit. Factories em `tests/conftest.py` (`FactoryUser`, `FactoryEletronico`, `FactoryContrato`).

```python
@pytest.mark.asyncio
async def test_xxx(async_client, login_teste):
    ...
```

## Convenções

- **Ruff** com `line-length = 79`, aspas simples, preview rules. `migrations/` excluído.
- Sempre rode `task format` antes de commitar; `task test` roda o lint antes do pytest.
- Schemas: `XCreate`, `XUpdate` (campos opcionais), `XRead`, `XList`.
- Trailing slash: collections (`/users/`, `/contratos/`) têm barra final; resources com ID (`/users/{id}`) não. FastAPI redireciona 307 entre as variantes.
