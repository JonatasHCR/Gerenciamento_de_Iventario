# InvControl — Backend

API FastAPI para o sistema de gerenciamento de inventário InvControl.

**Stack:** Python 3.13 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL (asyncpg) · Alembic · Pydantic v2 · PyJWT · pwdlib (Argon2) · Poetry · Ruff · Pytest

## Setup local

```bash
cd backend
poetry install
cp .env.example .env       # ajuste DB_USER, DB_PASSWORD, SECRET_KEY, etc.
alembic upgrade head
task run                   # fastapi dev backend/app.py → http://localhost:8000
```

Acesse a documentação interativa em `http://localhost:8000/docs`.

## Variáveis de ambiente

| Var | Exemplo | Descrição |
|---|---|---|
| `ENGINE_ASYNC` | `postgresql+asyncpg` | Driver SQLAlchemy async |
| `ENGINE_SYNC` | `postgresql+psycopg2` | (Não usado em runtime; Alembic é async via asyncpg) |
| `DB_USER`, `DB_PASSWORD` | `invcontrol` | Credenciais Postgres |
| `DB_HOST`, `DB_PORT` | `localhost` / `5432` | Host e porta |
| `DB_NAME` | `invcontrol` | Nome do banco |
| `SECRET_KEY` | string forte | Chave para assinar JWT |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Validade do token (em minutos) |

## Estrutura

```
backend/
├── backend/
│   ├── app.py              # Cria app FastAPI + CORS + registra routers
│   ├── core/               # Settings, EngineApp, database (Base)
│   ├── model/              # Modelos SQLAlchemy (Base)
│   ├── schemas/            # Pydantic v2 (Create, Update, Read, List)
│   ├── routers/            # Handlers HTTP finos; chamam services
│   ├── service/            # Regras de negócio + permissões
│   └── security/           # JWT, hash, dependências de auth
├── migrations/             # Alembic (env.py async)
├── tests/                  # Pytest + factory-boy + httpx
└── pyproject.toml          # Poetry + Ruff + Taskipy
```

## Comandos (via `task`)

```bash
task run        # fastapi dev
task lint       # ruff check
task format     # ruff check --fix && ruff format
task test       # pytest -s -x --cov=backend -vv (+ coverage html)
```

## Migrations

```bash
alembic revision --autogenerate -m "descrição"
alembic upgrade head
alembic downgrade -1
```

> ⚠️ Alembic **não** detecta `CheckConstraint`. Escreva-os manualmente em `op.create_check_constraint()` / `op.drop_constraint(...)`.

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

Use `ctx.assert_cc(cc)` e `ctx.assert_write(*tipos)` para enforcement de permissões. Ambos bypassam para Admin; nenhum bypassa para `Tecnico_TI`.

### Hierarquia de papéis (`User.tipo`)

| Papel | Capabilities |
|---|---|
| `Admin` | Acesso total |
| `Tecnico_TI` | Total em eletrônicos/associações de eletrônicos; leitura de tudo; sem aprovar/rejeitar solicitações |
| `Gestor` | Gerencia seu CC: aprova entradas, convida, gerencia equipamentos e membros |
| `Subgestor` | Como Gestor mas só `Funcionario` |
| `Funcionario` | Vê só seu CC e os eletrônicos a ele associados |

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
- `POST /solicitacoes/cessao` — payload `{ eletronico_ids, responsavel, centro_custo_destino }`
- O solicitante deve ser **Subgestor** dos CCs dos itens — e todos os itens precisam ser do **mesmo CC de origem** + estarem `Interno`.
- A solicitação carrega os equipamentos via `tb_solicitacao_eletronico` (N:N).
- Aprovar: Admin OU Gestor do CC de origem. Ao aprovar, o service **cria a `Cessao` automaticamente** (marca os itens como `Externo`, registra `cedido_por_id = ctx.user.id`).
- Rejeitar / cancelar: comportamento padrão (não move itens).

Visibilidade no GET:
- Admin → todas
- Gestor → suas CCs (entrada + cessão) + as próprias
- Subgestor → suas CCs (só `entrada_cc` de `Funcionario`) + as próprias
- Demais → apenas as próprias (`solicitante_id == ctx.user.id`)

### Exclusão (`DELETE /solicitacoes/{id}`)

- **Admin**: apaga qualquer solicitação, em **qualquer status** (`pendente`, `aprovada`, `rejeitada`), sem restrição de CC.
- Solicitante: cancela apenas as próprias `pendente`.
- Demais: 403.

## Autorização **per-CC** (ocupação, não tipo global)

**Regra crítica:** permissões em recursos de um CC dependem da `ocupacao` do usuário **naquele CC** (em `tb_associacao_user_contrato`), não do `User.tipo` global.

| Recurso | Operação | Autorização per-CC |
|---|---|---|
| `Contrato` | update/delete do CC X | Admin OU ocupação = `Gestor` em X |
| `Eletronico` | create no CC X | Admin/TI OU ocupação ∈ {Gestor, Subgestor, Funcionario} em X (Funcionario → auto-associa a si mesmo) |
| `Eletronico` | update/delete | Admin/TI OU ocupação Gestor/Subgestor no CC do eletrônico OU (Funcionario no CC + dono via associação) |
| `AssociacaoUserContrato` | create/update/delete | Admin OU ocupação Gestor no CC (Subgestor pode criar/remover só `Funcionario`); self-removal permitido |
| `AssociacaoUserEletronico` | create/delete | Admin/TI OU Gestor/Subgestor no CC do eletrônico OU (Funcionario no CC + sua própria associação) |

**Implementação:** `UserContext.assert_cc_role(cc, *roles)` em `security/dependencies.py`. Admin sempre bypassa. Tecnico_TI **não** bypassa nesse helper — quem chama decide explicitamente (em eletrônicos, ele tem `is_tecnico_ti` check separado).

Métodos auxiliares: `ctx.ocupacao_in(cc)` retorna a string da ocupação ou None.

**Implicação importante:** um usuário com `tipo='Gestor'` (global) que é só `Funcionario` no CC X **não tem** privilégios de Gestor em X. Inversamente, um `Funcionario` (global) que é Gestor em CC Y tem privilégios completos de Gestor em Y.

## Visibilidade e self-removal de CCs

- `GET /contratos/`: **todos os usuários autenticados veem todos os CCs**. Necessário pra Funcionário/Subgestor/Gestor descobrirem outros CCs e solicitarem entrada. Permissões de write (create/update/delete) continuam restritas a Gestor/Admin do próprio CC.
- `DELETE /associacoes/contratos/{user_id}/{cc}`: agora permite **self-removal** (qualquer usuário sai do CC se `user_id == ctx.user.id`). Quem remove outros segue regras antigas (Admin/TI/Gestor/Subgestor com restrição). Em ambos os casos, **bloqueia 409** se o usuário a ser removido é o único `Gestor` do CC — outro Gestor precisa ser nomeado antes.

## Paginação e filtros (`GET /eletronicos/`)

Endpoint principal de listagem de equipamentos suporta **filtros server-side + paginação**:

**Query params:**
| Param | Tipo | Descrição |
|---|---|---|
| `q` | string | Busca full-text em `nome`, `numero_serie`, `numero_patrimonio`, `marca`, `modelo`, `ip`, `localizacao` (ILIKE `%q%`) |
| `centro_custo` | list[str] | Filtra por CCs (pode repetir: `?centro_custo=A&centro_custo=B`) |
| `status` | list[str] | Filtra por status (`Interno`, `Externo`, `Em Manutenção`) |
| `tipo` | list[str] | Filtra por tipo |
| `page` | int ≥1 | Página (1-indexed). Default: 1 |
| `page_size` | int 1–1000 | Itens por página. Default: 50 |

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

**Helper de paginação** em `backend/core/pagination.py`: `paginate(session, query, page, page_size) → (items, total, pages)` — reutilizável em outros services.

## Cessões de equipamentos (`/cessoes`)

Histórico persistido de cessões com suporte a **devolução parcial em múltiplos lotes**.

**Modelo:**
- `Cessao`: `responsavel`, `centro_custo_destino`, `cedido_em`, `cedido_por_id`, `devolvida_em`, `devolvida_por_id` (preenchidos automaticamente quando o último item retorna).
- `CessaoEletronico` (N:N): cada linha carrega `devolvido_em`, `devolvida_por_id`, `devolucao_lote` (1, 2, 3… sequencial por cessão) e `gestor_visto_em`.
- Status derivado: `ativa` (zero devolvidos), `parcial` (alguns devolvidos), `devolvida` (todos).

**Endpoints:**

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/cessoes/` | Lista cessões visíveis com `eletronicos[]`, `devolucoes[]` agrupadas por lote, `status`, `total_devolvidos`, `total_pendentes` |
| `GET` | `/cessoes/{id}` | Detalhes da cessão (para reimprimir termo) |
| `POST` | `/cessoes/` | Cria cessão — marca equipamentos como `Externo` |
| `PUT` | `/cessoes/{id}/devolver` | Devolve **alguns** ou todos os itens: body `{ eletronico_ids, devolvida_em? }`. Próximo `devolucao_lote` é alocado e `Eletronico.status` volta a `Interno`. |
| `DELETE` | `/cessoes/{id}` | Apaga a cessão. Itens ainda externos voltam para `Interno` e localização é zerada. |
| `GET` | `/cessoes/recebimentos/pendentes-gestor` | Lista lotes ainda não vistos (para notificação) |
| `PUT` | `/cessoes/recebimentos/visto` | Marca todos os pendentes do usuário como vistos |

Payload do POST:
```json
{
  "eletronico_ids": [1, 2, 3],
  "responsavel": "Nome completo",
  "centro_custo_destino": "4549"
}
```

**Permissões — criar:**
- **Admin / Tecnico_TI**: qualquer CC.
- **Gestor**: apenas equipamentos em CCs onde sua `ocupacao == 'Gestor'`.
- **Subgestor**: ❌ direto — usa `POST /solicitacoes/cessao` que vai ao Gestor (ver Solicitações).
- **Demais**: ❌.

**Permissões — devolver (registrar recebimento):**
- **Admin / Tecnico_TI**: qualquer cessão.
- **Qualquer membro do CC**: registra a devolução em cessões cujos equipamentos pertencem a um CC onde ele tem **qualquer ocupação** (Gestor, Subgestor ou Funcionario). `devolvida_por_id` grava quem foi.

**Permissões — excluir:**
- **Admin**: qualquer cessão, sem restrição de CC.
- **Gestor**: apenas cessões com ao menos um item em CC onde sua `ocupacao == 'Gestor'`.
- **Demais**: ❌.

A criação é atômica: se qualquer ID falhar (404, sem permissão ou já `Externo`), a transação é abortada.

### Notificações de recebimento

Sempre que uma devolução é registrada, fica marcada `gestor_visto_em IS NULL`. Os endpoints `/cessoes/recebimentos/pendentes-gestor` e `PUT /cessoes/recebimentos/visto` servem para o frontend mostrar um badge contador.

Quem é notificado:

| Papel | Vê quais devoluções pendentes |
|---|---|
| **Admin** | **Todas**, sem restrição de CC |
| **Tecnico_TI** | **Todas**, sem restrição de CC |
| **Gestor** | Apenas dos CCs onde tem `ocupacao = 'Gestor'` |
| Demais | Nenhuma (endpoint retorna `count: 0`) |

Estado de "visto" é **compartilhado** entre supervisores — quando qualquer Admin/TI/Gestor visualiza, todos os pendentes em escopo do supervisor são marcados via `gestor_visto_em = now()`.

## Validações no model

- `Eletronico.tipo IN ('Computador', 'Notbook', 'Monitor', 'Impressora', 'Scanner')` — `check_tipo_eletronico_valid`
- `Eletronico.status IN ('Interno', 'Externo', 'Em Manutenção')` — `check_status_valid`
- `Eletronico.centro_custo` FK para `tb_contratos.centro_custo` (CASCADE)
- `User.tipo IN ('Admin', 'Funcionario', 'Gestor', 'Subgestor', 'Tecnico_TI')` — `check_tipo_valid`

## Testes

```bash
task test                                                # tudo
pytest tests/routers_tests/test_router_users.py -s -x -vv    # único arquivo
pytest -k "test_create_user" -vv                         # filtro por nome
```

Tests usam SQLite (`aiosqlite`) em memória via override do `EngineApp.get_async_session`. Factories em `tests/factories/`.

```python
@pytest.mark.asyncio
async def test_xxx(async_client, login_teste):
    ...
```

## Convenções

- **Ruff** com `line-length = 79`, aspas simples, preview rules. `migrations/` excluído.
- Sempre rode `task format` antes de commitar.
- Schemas: `XCreate`, `XUpdate` (campos opcionais), `XRead`, `XList`.
- Trailing slash: as collections (`/users/`, `/contratos/`) têm barra final; resources com ID (`/users/{id}`) não. FastAPI redireciona 307 entre as variantes.
