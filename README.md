
# PRIMEIRA ETAPA

## IDEALIZAÇÃO DO PROJETO

Este projeto tem como objetivo o controle de inventário da empresa, tanto internos quanto externos.  
Inicialmente, o sistema será focado no gerenciamento de aparelhos tecnológicos, como computadores, notebooks e periféricos.  
Futuramente, o escopo será ampliado para incluir o controle de outros bens patrimoniais, como mesas, cadeiras e demais itens físicos.

## MAPEAMENTO DE REQUESITOS

O escopo deste projeto restringe-se ao desenvolvimento de um sistema destinado ao cadastro e ao controle de aparelhos tecnológicos pertencentes à empresa. Além disso, o sistema deverá possibilitar a geração de relatórios gerenciais, com a finalidade de auxiliar no monitoramento e na gestão dos equipamentos, organizando-os por centro de custo ou por responsável (gestor).

### PERFIL: FUNCIONARIO

O usuário com perfil Funcionário possui permissões restritas à gestão dos aparelhos tecnológicos vinculados ao seu cadastro. Suas funcionalidades incluem:

- Cadastrar aparelhos tecnológicos associados ao próprio usuário;

- Editar informações dos aparelhos cadastrados;

- Excluir aparelhos tecnológicos vinculados ao seu perfil.

As operações realizadas por esse perfil são limitadas exclusivamente aos equipamentos sob sua responsabilidade.

### PERFIL: SUB-GESTOR

O usuário com perfil Subgestor possui todas as permissões atribuídas ao perfil Funcionário, acrescidas das seguintes funcionalidades administrativas no âmbito do centro de custo ao qual está vinculado:

- Adicionar funcionários ao centro de custo sob sua responsabilidade;

- Remover funcionários do centro de custo;

- Gerar relatórios contendo o inventário e o controle de todos os equipamentos vinculados ao centro de custo ou ao gestor responsável.

### PERFIL: GESTOR

O usuário com perfil Gestor possui todas as permissões atribuídas ao perfil Sub-gestor, além de funcionalidades adicionais relacionadas à gestão administrativa e contratual:

- Criar contratos vinculados ao seu centro de responsabilidade;

- Editar contratos existentes;

- Excluir contratos;

- Nomear usuários com perfil de Sub-gestor;

- Exportar equipamentos da empresa para contratos de sua responsabilidade.

## MODELAGEM

- Diagrama de Casos de Uso

- Modelo Conceitual

- Modelo Lógico

- Modelo Físico

- Protótipo


# SEGUNDA ETAPA

- MVP do projeto

---

# REGRAS DE NEGÓCIO DETALHADAS

## CADASTRO E ACESSO DE USUÁRIOS

- **Auto-registro** é permitido: qualquer pessoa pode se cadastrar no sistema, mas o perfil criado será sempre `Funcionario`.
- Para obter um perfil superior (`Subgestor`, `Gestor`), o usuário deve enviar uma **solicitação** ao Gestor ou Subgestor responsável pelo centro de custo desejado, ou ao Administrador do sistema.
- Somente `Admin` e `Tecnico_TI` podem criar usuários com qualquer perfil diretamente via API.
- **Qualquer usuário autenticado pode editar apenas o próprio perfil** (nome, email, senha). Não é permitido alterar o próprio `tipo`.
- `Admin` e `Tecnico_TI` podem editar o perfil de qualquer usuário, incluindo o campo `tipo`.
- Apenas `Admin` e `Tecnico_TI` podem excluir usuários.

## VISIBILIDADE DE USUÁRIOS

| Perfil | Quem pode ver |
|---|---|
| `Admin` / `Tecnico_TI` | Todos os usuários |
| `Gestor` / `Subgestor` | Todos os usuários do sistema (para poder enviar solicitações de associação) |
| `Funcionario` | Apenas usuários associados ao mesmo centro de custo |

## REGRAS POR RECURSO

### Eletrônicos (`/eletronicos`)

| Operação | Admin / TI | Gestor | Subgestor | Funcionario |
|---|---|---|---|---|
| Listar | Todos | Apenas do seu CC | Apenas do seu CC | Apenas os associados a si |
| Criar | Qualquer CC | Apenas seu CC | Apenas seu CC | Apenas seu CC |
| Editar | Qualquer | Apenas do seu CC | Apenas do seu CC | Apenas os associados a si |
| Excluir | Qualquer | Apenas do seu CC | Apenas do seu CC | Apenas os associados a si |

- Um eletrônico pertence a um centro de custo via o campo `centro_custo`.
- Um Funcionário gerencia apenas os eletrônicos diretamente associados a ele via `tb_associacao_user_eletronico`.

### Contratos (`/contratos`)

| Operação | Admin / TI | Gestor           | Subgestor        | Funcionario                |
| -------- | ---------- | ---------------- | ---------------- | -------------------------- |
| Listar   | Todos      | Apenas do seu CC | Apenas do seu CC | Apenas do seu CC (leitura) |
| Criar    | Qualquer   | Qualquer         | ❌                | ❌                          |
| Editar   | Qualquer   | Apenas seu CC    | ❌                | ❌                          |
| Excluir  | Qualquer   | Apenas seu CC    | ❌                | ❌                          |

- Funcionário pode listar contratos do seu centro de custo apenas para leitura, por exemplo, para identificar a qual gestor/subgestor enviar uma solicitação de associação.

### Associações Usuário–Contrato (`/associacoes/contratos`)

| Operação | Admin / TI | Gestor | Subgestor | Funcionario |
|---|---|---|---|---|
| Listar | Todos | Apenas do seu CC | Apenas do seu CC | Apenas do seu CC |
| Criar | Qualquer | Seu CC, qualquer ocupação | Seu CC, apenas `Funcionario` | ❌ |
| Editar ocupação | Qualquer | Apenas seu CC | ❌ | ❌ |
| Remover | Qualquer | Apenas seu CC | Seu CC, apenas `Funcionario` | ❌ |

- Gestor pode nomear Subgestores (criar associação com `ocupacao = 'Subgestor'`).
- Subgestor só pode adicionar e remover Funcionários — nunca alterar ocupações de Gestores ou outros Subgestores.

### Associações Usuário–Eletrônico (`/associacoes/eletronicos`)

| Operação | Admin / TI | Gestor | Subgestor | Funcionario |
|---|---|---|---|---|
| Listar | Todos | Do seu CC | Do seu CC | Apenas as próprias |
| Criar | Qualquer | Eletronico do CC | Eletronico do CC | Apenas para si mesmo |
| Remover | Qualquer | Eletronico do CC | Eletronico do CC | Apenas as próprias |

### Cessões (`/cessoes`)

Histórico persistido de cessões de equipamentos. Permite cessão parcial — múltiplas devoluções (lotes) por cessão até que tudo retorne.

| Operação | Admin / TI | Gestor (do CC) | Subgestor (do CC) | Demais membros do CC |
|---|---|---|---|---|
| Listar | Todas | Suas + envolvendo seu CC | Suas + envolvendo seu CC | Apenas as próprias |
| Criar | Qualquer CC | Apenas equipamentos dos seus CCs | ❌ — envia **solicitação** ao Gestor | ❌ |
| Devolver (registrar recebimento) | Qualquer | Sim | Sim | **Sim** — qualquer membro do CC pode receber |
| Excluir | **Qualquer (sem restrição)** | Apenas cessões com itens dos seus CCs | ❌ | ❌ |

- A devolução pode ser **parcial**: ao clicar em "Devolver" o usuário escolhe quais equipamentos estão retornando. A cessão fica em estado `Parcial X/Y` até a última peça voltar.
- Cada lote de devolução gera seu próprio **Termo de Recebimento**, identificado por número (#1, #2, …), reabrível a qualquer momento.
- O **Termo de Recebimento** registra o **responsável que devolveu** + o **membro do CC que recebeu** (qualquer ocupação) + uma assinatura de **Visto do Gestor do CC**.
- Ao excluir uma cessão em aberto, os itens ainda externos voltam para `Interno` e a localização é zerada.

### Solicitação de cessão (Subgestor → Gestor)

Como Subgestor não pode criar cessões diretamente, o fluxo de cessão para ele passa por uma solicitação:

1. Subgestor abre `/equipamentos/ceder`, seleciona equipamentos do **seu CC** (CC único), define responsável e CC destino, e envia a solicitação.
2. A solicitação aparece em `/solicitacoes` para o **Gestor do CC de origem** (ou Admin), com link para o **Termo (proposta)** mostrando todos os equipamentos.
3. Gestor aprova → o backend cria a `Cessao` automaticamente, marca os equipamentos como `Externo` e gera o termo definitivo.
4. Gestor rejeita → status `rejeitada`, nada acontece com os itens.

### Notificações ao supervisor

Quando um membro do CC registra a devolução de um equipamento, o sistema notifica via badge no menu lateral (item **Cessões**):

- **Admin** e **Tecnico_TI** recebem notificações de **todas** as devoluções, **sem restrição de CC**.
- **Gestor** recebe notificações **apenas** das devoluções em CCs onde tem ocupação `Gestor`.
- Polling de 5 s atualiza o contador. O badge zera quando o supervisor abre a página `/cessoes`. Cada devolução não-vista também é marcada com um selo "Novo" inline.
- Estado de "visto" é **compartilhado** entre supervisores — quando qualquer Admin/TI/Gestor reconhece a devolução, a notificação some para os demais.

## FLUXO DE SOLICITAÇÃO DE ASSOCIAÇÃO A CENTRO DE CUSTO

1. Funcionário visualiza a lista de contratos disponíveis e identifica o centro de custo desejado.
2. Funcionário envia uma solicitação ao Gestor ou Subgestor do centro de custo.
3. Gestor ou Subgestor aprova ou rejeita a solicitação.
4. Em caso de aprovação, a associação é criada automaticamente com a `ocupacao` solicitada (Subgestor só pode aprovar `Funcionario`).

### Outros tipos de solicitação

- **`convite_cc`**: Gestor/Subgestor convida um usuário existente para entrar no seu CC. O próprio convidado aceita ou rejeita.
- **`cargo_inicial`**: usuário pede ao Admin um cargo global acima de `Funcionario` (`Subgestor`, `Gestor`, `Tecnico_TI`).
- **`cessao`**: Subgestor solicita cessão de equipamentos ao Gestor do CC (ver acima).

### Exclusão de solicitações

- **Admin** pode excluir **qualquer solicitação**, em **qualquer status** (`pendente`, `aprovada`, `rejeitada`), sem restrição de CC.
- O próprio solicitante pode cancelar apenas suas solicitações `pendente`.