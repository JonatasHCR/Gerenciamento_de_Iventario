
# PRIMEIRA ETAPA

## IDEALIZAÇÃO DO PROJETO

Este projeto tem como objetivo o controle de inventário de ativos da empresa, tanto internos quanto externos.  
Inicialmente, o sistema será focado no gerenciamento de aparelhos tecnológicos, como computadores, notebooks e periféricos.  
Futuramente, o escopo será ampliado para incluir o controle de outros bens patrimoniais, como mesas, cadeiras e demais itens físicos.

## MAPEAMENTO DE REQUESITOS

O escopo deste projeto restringe-se ao desenvolvimento de um sistema destinado ao cadastro e ao controle de aparelhos tecnológicos pertencentes à empresa. Além disso, o sistema deverá possibilitar a geração de relatórios gerenciais, com a finalidade de auxiliar no monitoramento e na gestão dos equipamentos, organizando-os por centro de custo ou por responsável (gestor).

### PERFIL: FUNCIONARIO

O usuário com perfil Funcionário possui permissões restritas à gestão dos aparelhos tecnológicos vinculados ao seu cadastro. Suas funcionalidades incluem:

Cadastrar aparelhos tecnológicos associados ao próprio usuário;

Editar informações dos aparelhos cadastrados;

Excluir aparelhos tecnológicos vinculados ao seu perfil.

As operações realizadas por esse perfil são limitadas exclusivamente aos equipamentos sob sua responsabilidade.

### PERFIL: SUB-GESTOR

O usuário com perfil Subgestor possui todas as permissões atribuídas ao perfil Funcionário, acrescidas das seguintes funcionalidades administrativas no âmbito do centro de custo ao qual está vinculado:

Adicionar funcionários ao centro de custo sob sua responsabilidade;

Remover funcionários do centro de custo;

Gerar relatórios contendo o inventário e o controle de todos os equipamentos vinculados ao centro de custo ou ao gestor responsável.

### PERFIL: GESTOR

O usuário com perfil Gestor possui todas as permissões atribuídas ao perfil Subgestor, além de funcionalidades adicionais relacionadas à gestão administrativa e contratual:

Criar contratos vinculados ao seu centro de responsabilidade;

Editar contratos existentes;

Excluir contratos;

Nomear usuários com perfil de Subgestor;

Exportar equipamentos da empresa para contratos de sua responsabilidade.