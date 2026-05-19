# InvControl — Frontend

Aplicação web do InvControl em **Next.js 16** (App Router) com TypeScript, Tailwind CSS v4 e shadcn/ui.

**Stack:** Next.js 16 · React 19 · TypeScript · Tailwind v4 · shadcn/ui · next-themes · sonner · lucide-react

## Setup local

```bash
cd frontend/frontend
npm ci
npm run dev          # http://localhost:3000 (com Turbopack)
```

O backend precisa estar rodando em `http://localhost:8000` (padrão) ou aponte com:

```bash
API_URL=http://meu-backend:8000 npm run dev
```

## Variáveis de ambiente

| Var | Padrão | Onde |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Server-side. Endereço do backend para o proxy. **Lida em runtime**, não precisa rebuild. |

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
│   ├── api/[...path]/route.ts    # Proxy reverso para o backend (server-side)
│   ├── login/                    # Login público
│   ├── cadastro/                 # Auto-cadastro público
│   ├── page.tsx                  # Dashboard
│   ├── centros-de-custo/         # CRUD de CCs + solicitação de entrada
│   ├── equipamentos/             # CRUD com tabela + filtros
│   ├── usuarios/                 # Lista por CC + criar/editar/convidar
│   ├── solicitacoes/             # Aprovar/rejeitar/cancelar
│   ├── layout.tsx                # Root layout (Providers + ConditionalLayout)
│   └── globals.css               # Tema (vermelho/branco/laranja, dark mode)
├── components/
│   ├── ui/                       # shadcn primitivos
│   └── app/                      # Componentes da aplicação
│       ├── providers.tsx         # ThemeProvider + AuthProvider + Toaster
│       ├── conditional-layout.tsx # Sidebar+Topbar OU layout centralizado (auth)
│       ├── sidebar.tsx           # Sidebar desktop colapsável
│       ├── mobile-sidebar.tsx    # Drawer mobile (Sheet)
│       ├── topbar.tsx            # Hambúrguer, toggle tema, sino de convites
│       └── searchable-select.tsx # Combobox custom (Input + filtro)
├── context/
│   └── auth-context.tsx          # AuthProvider, useAuth(), refresh polling 10s
├── lib/
│   ├── utils.ts                  # cn, cookies, decodeJwt, formatDate
│   └── api/
│       ├── client.ts             # apiFetch base, ApiError, refresh em 401
│       ├── auth.ts, users.ts, contratos.ts, eletronicos.ts,
│       └── associacoes.ts, solicitacoes.ts
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
- O proxy lê `req.nextUrl.pathname` (preserva barra final graças ao `skipTrailingSlashRedirect: true`)
- Lê body como `text()` (cloneable para redirects)
- `redirect: 'follow'` — segue os 307 do FastAPI dentro da rede
- `API_URL` é variável **server-side**, não `NEXT_PUBLIC_*` — pode mudar sem rebuild

## Autenticação

- Login (`POST /auth/login`) retorna `access_token` (JWT), salvo no cookie `invcontrol_token` (7 dias).
- `AuthProvider` decodifica o JWT (`sub` = email) e busca o usuário em `getUsers()` para hidratar `user`.
- `useAuth()` expõe `{ user, isLoading, login, logout }`.
- **Polling**: a cada 10 s rebusca o usuário — pega upgrades de `tipo` automaticamente após o admin aprovar uma solicitação.
- Em erros 401, o cookie é apagado e o usuário é deslogado. Erros transitórios de rede **não** deslogam.
- `middleware.ts` redireciona não-autenticados pra `/login` e autenticados em `/login`/`/cadastro` pra `/`.

## Páginas e papéis

| Página | Quem vê o quê |
|---|---|
| `/` (Dashboard) | Cards de totais (equipamentos, CCs, internos, cedidos, manutenção) + gráfico por tipo. Funcionario vê só seus equipamentos. |
| `/centros-de-custo` | Lista **todos os CCs** com filtro "Todos / Só meus / Que não faço parte". Cada card mostra código + descrição, **Gestor** à esquerda e **contagem de membros** à direita. Em CCs do usuário: botão **"Sair do CC"** (desabilitado se ele for o único Gestor). Em CCs que o usuário não faz parte (e não é Admin/TI): botão **"Solicitar entrada"** que abre dialog para escolher o **cargo desejado** (Gestor/Subgestor/Funcionario) — solicitação vai para o Gestor do CC. Gestor/Admin têm "Novo CC" / excluir. |
| `/equipamentos` | Tabela paginada (25/página) com filtros server-side: busca, **Select de campo de busca** (`Todos`, `Nome`, `Nº Série`, `Nº Patrimônio`, `Marca`, `Modelo`, `IP`, `Localização`, `Responsável`, `Sem responsável`), CC, status, tipo. "Sem responsável" desabilita o Input e filtra equipamentos sem associação. CRUD conforme papel. Coluna **Responsável** mostra o usuário associado. No formulário de criação, o campo Responsável aparece após escolher o CC — default é o próprio usuário; Funcionario no CC vê o campo travado. Botão **👥 Definir responsável** edita depois; **×** remove. Botão **Ceder** disponível para Admin/Tecnico_TI/Gestor/**Subgestor**. |
| `/equipamentos/ceder` | Multi-select de equipamentos internos + responsável + CC destino. Para **Admin/TI/Gestor**: submeter chama `POST /cessoes/`, abre o termo e redireciona para `/cessoes`. Para **Subgestor**: a tela vira "Solicitar cessão", esconde o campo de data, valida que todos os itens são de um único CC de origem, e envia `POST /solicitacoes/cessao` — a cessão real só é criada quando o Gestor aprova a solicitação. |
| `/cessoes` | Lista de cessões com badges `Ativa` / `Parcial X/Y` / `Devolvida`. Suporta **devolução parcial**: o diálogo "Devolver" mostra checkboxes só dos itens pendentes — desmarcar gera devolução parcial e a cessão fica em `Parcial` com a contagem. Cada devolução vira um **lote** com link próprio para o Termo de Recebimento (#1, #2…), com selo "Novo" em devoluções ainda não vistas pelo gestor. **Devolver** liberado para qualquer membro do CC (backend revalida). **Excluir** (vermelho) aparece para Admin (qualquer cessão) e Gestor (cessões dos seus CCs); itens em aberto voltam para `Interno`. Ao montar, marca pendentes do supervisor como vistos. |
| `/cessoes/[id]/termo` | Layout imprimível (A4) do **Termo de Responsabilidade**. Reabrível a qualquer momento. |
| `/cessoes/[id]/recebimento/[lote]` | Termo de Recebimento por lote. Cabeçalho indica "PARCIAL" quando aplicável + "Recebimento #N de M". Mostra **Recebido por** (membro do CC) + linha CC origem/destino + três assinaturas: **Devolve** (responsável), **Recebe** (membro do CC) e **Gestor do CC (Visto)**. |
| `/cessoes/[id]/recebimento` | Redireciona para o lote mais recente (compat com links antigos). |
| `/solicitacoes/[id]/termo` | Termo (proposta) de uma solicitação de cessão pendente — mesmo layout do termo de responsabilidade, marcado como "Proposta · Solicitação #N · pendente". Usado pelo Gestor para revisar a lista completa antes de aprovar. |
| `/relatorios` | Gerador de relatórios 100% dinâmico **agrupado por CC**. **Acesso (per-CC):** Admin/Tecnico_TI sempre; outros usuários **apenas se tiverem ocupação Gestor ou Subgestor em pelo menos um CC** (não depende do `tipo` global). Página redireciona se não autorizado; link some do menu (sidebar + mobile) na mesma regra. Gestor/Subgestor veem só equipamentos dos CCs onde têm essa ocupação; Admin/TI veem tudo. Filtros: CCs (multi-select), status, tipos. Atalho **"Filtrar por Gestor"** (Admin/TI). Cards colapsáveis por CC, contagem por CC. PDF agrupado. CSV com linha separadora. Botões **Excel (CSV)** + **PDF**. |
| `/usuarios` | Seções colapsáveis por CC + "Todos os usuários" (admin). Select de **campo de busca** (Todos / Nome / Email / Tipo). Admin: criar/editar/excluir; outros: convidar (para suas CCs). |
| `/solicitacoes` | Pendentes + histórico. Tipos: `entrada_cc`, `cargo_inicial`, `cessao` (Subgestor→Gestor). Convidado aceita/recusa próprio convite; Gestor/Subgestor aprovam entradas no seu CC; Gestor aprova cessões do seu CC (clica "Ver termo" para revisar a lista de equipamentos); Admin aprova tudo. **Admin pode excluir qualquer solicitação em qualquer status**; solicitante cancela só as próprias pendentes. |

## UI

- **Tema** (`globals.css`): vermelho primário + laranja accent + branco. Dark mode via `next-themes` (sem `system`), toggle 🌙/☀️ na topbar.
- **Mobile**: sidebar desaparece (`md:flex`), abre como drawer pelo botão ☰. Tabelas com `overflow-x-auto`. Grids/forms reorganizados.
- **Notificações em tempo real** (polling 5 s):
  - Badge na sidebar com **solicitações pendentes**
  - Badge na sidebar em **Cessões** com **recebimentos não vistos** — para **Admin/Tecnico_TI** conta **todas** sem restrição de CC; para **Gestor**, apenas dos CCs onde tem ocupação `Gestor`; demais não recebem. Estado de "visto" é compartilhado entre supervisores e zerado ao abrir `/cessoes`.
  - Sino na topbar com convites pessoais
  - `/solicitacoes` recarrega lista
- **Tratamento de erros**: `client.ts` formata `detail` (string ou array de validação 422 do FastAPI) em texto legível mostrado via `sonner`.

## Componentes utilitários

- **`SearchableSelect`** — usado para selects com muitas opções (CCs, usuários). Filtra ao digitar. Construído com Input + outside-click.
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

Em Docker: o `Dockerfile` faz build multi-stage e roda `node server.js` na imagem final.
