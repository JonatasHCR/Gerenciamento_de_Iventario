# InvControl — Frontend

Aplicação web do InvControl em **Next.js 16** (App Router) com TypeScript, Tailwind CSS v4 e shadcn/ui.

**Stack:** Next.js 16 · React 19 · TypeScript · Tailwind v4 · shadcn/ui · next-themes · sonner · lucide-react

## Setup local

```bash
cd frontend/frontend
npm ci
npm run dev          # http://localhost:3000 (com Turbopack)
```

O backend precisa estar acessível em `http://localhost:8000` (padrão) ou aponte com:

```bash
API_URL=http://meu-backend:8030 npm run dev
```

Em Docker (recomendado), tudo é orquestrado pelo `docker-compose.yml` da raiz — as portas reais vêm do `.env` (defaults nesse repo: frontend `3030`, backend `8030`).

## Variáveis de ambiente

| Var | Padrão | Onde |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Server-side. Endereço do backend pro proxy. **Lida em runtime**, sem rebuild. Em Docker é `http://backend:8000` (rede interna). |

## Comandos

```bash
npm run dev          # next dev --turbopack
npm run build        # next build (output: standalone)
npm run start        # next start
npm run lint         # eslint
npm run typecheck    # tsc --noEmit
npm run format       # prettier --write "**/*.{ts,tsx}"
```

## Estrutura

```
frontend/frontend/
├── app/
│   ├── api/[...path]/route.ts    # Proxy reverso pro backend (server-side)
│   ├── login/                    # Login público
│   ├── cadastro/                 # Auto-cadastro com select de domínio
│   ├── page.tsx                  # Dashboard
│   ├── centros-de-custo/         # CRUD de CCs + solicitação de entrada
│   ├── equipamentos/             # CRUD com tabela + filtros server-side
│   │   └── ceder/                # Cessão (ou solicitação, se Subgestor)
│   ├── cessoes/                  # Histórico + devolução parcial + termo
│   │   └── [id]/
│   │       ├── termo/            # Termo de Responsabilidade (saída)
│   │       └── recebimento/[lote]# Termo de Recebimento por lote
│   ├── usuarios/                 # Lista por CC + criar/editar/convidar
│   ├── solicitacoes/             # Aprovar/rejeitar/cancelar
│   │   └── [id]/termo/           # Proposta de termo (cessão pendente)
│   ├── tipos/                    # CRUD do catálogo de tipos (Admin)
│   ├── localizacoes/             # CRUD do catálogo de localizações (Admin)
│   ├── auditoria/                # Audit log paginado (Admin)
│   ├── relatorios/               # Relatórios em CSV/PDF
│   ├── layout.tsx                # Root layout
│   └── globals.css               # Tema + dark mode
├── components/
│   ├── ui/                       # shadcn primitivos + required-mark.tsx
│   └── app/                      # Componentes da aplicação
│       ├── providers.tsx         # ThemeProvider + AuthProvider + Toaster
│       ├── conditional-layout.tsx# Sidebar+Topbar OU layout centrado (auth)
│       ├── sidebar.tsx           # Sidebar desktop colapsável (com badges)
│       ├── mobile-sidebar.tsx    # Drawer mobile
│       ├── topbar.tsx            # Hambúrguer, tema, sino de convites
│       └── searchable-select.tsx # Combobox custom (Input + filtro)
├── context/
│   └── auth-context.tsx          # AuthProvider, useAuth(), refresh polling 10s
├── lib/
│   ├── utils.ts                  # cn, cookies, decodeJwt, formatDate
│   └── api/
│       ├── client.ts             # apiFetch base, ApiError, refresh em 401
│       ├── auth.ts, users.ts, contratos.ts, eletronicos.ts,
│       ├── associacoes.ts, solicitacoes.ts, cessoes.ts,
│       └── tipos.ts, localizacoes.ts, audit_log.ts
├── types/api.ts                  # Tipos espelhando schemas do backend
├── middleware.ts                 # Guard de rotas via cookie invcontrol_token
├── next.config.mjs               # output: standalone + skipTrailingSlashRedirect
└── package.json
```

## API proxy

Em vez de chamar o backend diretamente do navegador (o que exporia o host interno do Docker), todas as chamadas passam por uma API Route em `app/api/[...path]/route.ts`:

```
browser  →  /api/users/   →   Next.js server  →  http://backend:8000/users/
                                                  (segue 307 internamente)
```

Pontos importantes:
- `BASE_URL = '/api'` em `lib/api/client.ts` — todas as URLs ficam relativas
- O proxy lê `req.nextUrl.pathname` (preserva barra final via `skipTrailingSlashRedirect: true`)
- Lê body como `text()` (cloneable para redirects)
- `redirect: 'follow'` — segue os 307 do FastAPI dentro da rede Docker
- **Remove `content-length` e `content-encoding`** depois que `fetch()` descomprime — sem isso, responses gzipadas pelo backend ficavam truncadas no browser
- `API_URL` é variável **server-side** (não `NEXT_PUBLIC_*`) — pode mudar sem rebuild

## Autenticação

- Login (`POST /auth/login`) retorna `access_token` (JWT, TTL = `ACCESS_TOKEN_EXPIRE_MINUTES` do backend, default 60min), salvo no cookie `invcontrol_token`.
- `AuthProvider` decodifica o JWT (`sub` = email) e busca o usuário em `getUsers()` para hidratar `user`.
- `useAuth()` expõe `{ user, isLoading, login, logout }`.
- **Refresh transparente**: `client.ts` chama `/auth/refresh_token` automaticamente em 401 e refaz a request original. Usuário ativo nunca cai pro login enquanto estiver com o navegador aberto.
- **Polling de user**: 10s — pega upgrades de `tipo` automáticos após Admin aprovar.
- Em 401 sustentado (refresh também falha), cookie é apagado e usuário desloga. Erros transitórios de rede **não** deslogam.
- `middleware.ts` redireciona não-autenticados pra `/login` e autenticados em `/login`/`/cadastro` pra `/`.

## Páginas e papéis

| Página | Quem vê | O quê |
|---|---|---|
| `/` (Dashboard) | Todos | Cards de totais + gráfico por tipo. Funcionario vê só seus equipamentos. |
| `/cadastro` | Público | Auto-registro. Email dividido em local-part + select de domínio (`@ufcengenharia.com.br` ou `@sememail.com`). Backend valida contra `ALLOWED_EMAIL_DOMAINS`. Senha mínima 8 chars. |
| `/login` | Público | Email + senha. Senha com ícone 👁/🚫 pra mostrar/esconder. |
| `/centros-de-custo` | Todos | Lista todos os CCs com filtro "Todos / Só meus / Que não faço parte". Em CCs do usuário: botão **Sair do CC**; em CCs alheios: **Solicitar entrada** (dialog com cargo). Gestor/Admin têm **Novo CC** / Excluir. |
| `/equipamentos` | Todos (visão per-papel) | Tabela paginada (25/página) com filtros server-side: busca, **Select de campo** (Todos, Nome, Nº Série, Patrimônio, Marca, Modelo, IP, Localização, **Responsável**, **Sem responsável**), CC, status, tipo. Form de novo equipamento: tipos vêm do catálogo dinâmico; **Localização** é um SearchableSelect com botão **+** pra criar nova localização inline (qualquer usuário); checkbox **"Equipamento sem IP"**; **Descrição** é textarea; **Nº Série** é convertido pra maiúsculas automaticamente ao digitar. Botão **Ceder** disponível pra Admin/TI/Gestor/Subgestor. |
| `/equipamentos/ceder` | Admin/TI/Gestor/Subgestor | Multi-select de equipamentos internos + responsável + CC destino. Admin/TI/Gestor cria cessão direta; **Subgestor** envia `solicitacao.cessao` ao Gestor (a tela vira "Solicitar cessão", esconde data, valida CC origem único). |
| `/cessoes` | Todos (visão per-papel) | Lista com badges `Ativa` / `Parcial X/Y` / `Devolvida`. **Devolução parcial**: dialog mostra checkboxes só dos itens pendentes; cada devolução vira um lote com termo próprio (#1, #2…). **Devolver** liberado pra qualquer membro do CC (backend revalida). **Excluir** (Admin sem restrição; Gestor dos seus CCs). Selo **"Novo"** em devoluções não vistas pelo supervisor; abrir a página marca como vistas. |
| `/cessoes/[id]/termo` | Todos com acesso | Termo de Responsabilidade (A4 imprimível). Reabrível a qualquer momento. |
| `/cessoes/[id]/recebimento/[lote]` | Todos com acesso | Termo de Recebimento por lote. Cabeçalho indica "PARCIAL" + "Recebimento #N de M". Mostra **Recebido por** (membro do CC) + 3 assinaturas: Devolve, Recebe e Gestor do CC (Visto). |
| `/cessoes/[id]/recebimento` | — | Redirect pro lote mais recente (compat de links). |
| `/solicitacoes` | Todos (visão per-papel) | Pendentes + histórico. Tipos: `entrada_cc`, `cargo_inicial`, `cessao`. Botão **Ver termo** em solicitações de cessão. **Admin** pode excluir em qualquer status; solicitante cancela só as próprias pendentes. |
| `/solicitacoes/[id]/termo` | Admin/Gestor | Proposta de termo de uma solicitação `cessao` pendente. |
| `/usuarios` | Todos (visão per-papel) | Seções colapsáveis por CC + "Todos os usuários" (Admin). Select de **campo de busca** (Todos / Nome / Email / Tipo). Admin: criar/editar/excluir. Em cada membro do CC: ícone 🛡️ **"Mudar cargo"** (Admin sempre; Gestor do CC para membros não-Gestor); ícone 🗑️ pra remover (regras de associação). SearchableSelect de "Convidar usuário" exibe só o nome no input mas filtra por nome+email. |
| `/relatorios` | Admin/TI sempre; demais só se tiverem ocupação Gestor/Subgestor em algum CC | Gerador de relatórios filtráveis e exportáveis. **Agrupamento dinâmico**: CC (padrão), Localização, Responsável, Status, Tipo ou Marca. **Filtros**: CCs (multi-select), Localização (pesquisável, multi-select, padrão = todas), Status, Tipo; **atalho multi-select de Gestor** (Admin/TI) auto-popula os CCs dos gestores selecionados. **Seletor de colunas** personalizável. **CSV** (UTF-8 BOM, separador `;`). **PDF** via `window.print()`: cabeçalho de grupo repetido em cada página via `thead`, rodapé "continua na próxima página ↓" via `tfoot` (só aparece quando a tabela de fato quebra). IP em branco aparece como **"Sem IP"**. |
| `/tipos` | **Admin** | CRUD do catálogo de tipos de equipamento. Soft-delete (`ativo=false`) quando há equipamentos usando; rename faz cascade no `tipo` dos eletrônicos. |
| `/localizacoes` | **Admin** | CRUD do catálogo de localizações. Rename faz cascade na `localizacao` dos eletrônicos. Criação inline pelo form de equipamento (qualquer usuário) → admin organiza aqui. |
| `/auditoria` | **Admin** | Lista paginada de `tb_audit_log` com filtros (ação, recurso, autor). Cada linha mostra ação, recurso, autor (resolvido em nome) e payload JSON colapsável. Badges coloridas: vermelha pra deletes/removes. |

## UI

- **Tema** (`globals.css`): vermelho primário + laranja accent + branco. Dark mode via `next-themes` (sem `system`), toggle 🌙/☀️ na topbar.
- **Mobile**: sidebar desaparece (`md:flex`), abre como drawer pelo ☰. Tabelas com `overflow-x-auto`. Grids/forms reorganizados.
- **Notificações em tempo real** (polling 5 s):
  - Badge na sidebar com **solicitações pendentes**
  - Badge na sidebar em **Cessões** com **recebimentos não vistos** — para Admin/Tecnico_TI conta **todas** sem restrição de CC; para Gestor, apenas dos CCs onde tem ocupação `Gestor`; demais não recebem. Estado de "visto" é compartilhado entre supervisores e zerado ao abrir `/cessoes`.
  - Sino na topbar com convites pessoais
  - `/solicitacoes` recarrega lista
- **Tratamento de erros**: `client.ts` formata `detail` (string ou array 422 do FastAPI) em texto legível, exibido via `sonner`.
- **Asterisco em campos obrigatórios**: `components/ui/required-mark.tsx` (`<RequiredMark />`) é usado em todos os forms de cadastro/edição. Login não usa (todos os campos são óbvios).

## Componentes utilitários

- **`SearchableSelect`** — combobox custom (`Input` + outside-click). Usado pra selects com muitas opções (CCs, usuários, localizações). Aceita prop opcional `searchKey` pra dissociar **label** (exibição enxuta) do **texto pesquisável** (ex.: convite de usuário mostra só `nome` mas filtra por `nome + email`).
- **`Textarea`** — primitivo shadcn-style para campos multi-linha (descrição de equipamento).
- **`RequiredMark`** — `*` vermelho com `aria-label="obrigatório"` (acessível pra leitores de tela).
- Tipagem de erros: `ApiError extends Error` com `status: number`.

## Convenções

- Prettier + ESLint (next) configurados. Rode `npm run format` antes de commitar.
- Imports absolutos via `@/...`.
- Componentes de página em `app/.../page.tsx` (`'use client'` quando usam estado/efeitos).
- API client única em `lib/api/client.ts` — não use `fetch` direto em páginas.
- `autoComplete` correto nos campos de senha (`new-password` em criação/edição, `current-password` no login) pra evitar interferência do gerenciador de senhas.

## Build de produção

```bash
npm run build
node .next/standalone/server.js   # roda standalone (HOSTNAME=0.0.0.0 PORT=3000)
```

Em Docker: o `Dockerfile` faz build multi-stage e roda `node server.js` na imagem final. A porta exposta pelo host vem de `FRONTEND_PORT` no `.env` da raiz.
