"""remove índices redundantes em várias tabelas

Auditoria de índices encontrou redundâncias acumuladas no histórico de
migrations (schema inicial + f4b2d7a9c3e1) e por `index=True` em colunas
que já têm índice via PK ou UNIQUE:

- Duplicatas exatas (mesma coluna, dois nomes):
  ix_assoc_user_contrato_user_id, ix_cessoes_cedido_por_id,
  ix_solicitacoes_solicitante_id
- Prefixo coberto por índice composto:
  ix_solicitacoes_status  (coberto por ix_sol_status_centro_custo)
- Redundantes com a PK:
  ix_tb_audit_log_id, ix_tb_cessoes_id, ix_tb_eletronicos_id,
  ix_tb_users_id, ix_tb_contratos_centro_custo
- Redundantes com UNIQUE(nome):
  ix_tb_localizacoes_nome, ix_tb_marcas_nome

Dropar índice nunca quebra query — só remove custo de escrita/armazenamento.

Revision ID: d4e7b2a9c6f3
Revises: c8f1a4d7e2b3
Create Date: 2026-06-26 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4e7b2a9c6f3'
down_revision: Union[str, Sequence[str], None] = 'c8f1a4d7e2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nome_do_indice, tabela)
_REDUNDANTES = [
    ('ix_assoc_user_contrato_user_id', 'tb_associacao_user_contrato'),
    ('ix_cessoes_cedido_por_id', 'tb_cessoes'),
    ('ix_solicitacoes_solicitante_id', 'tb_solicitacoes'),
    ('ix_solicitacoes_status', 'tb_solicitacoes'),
    ('ix_tb_audit_log_id', 'tb_audit_log'),
    ('ix_tb_cessoes_id', 'tb_cessoes'),
    ('ix_tb_eletronicos_id', 'tb_eletronicos'),
    ('ix_tb_users_id', 'tb_users'),
    ('ix_tb_contratos_centro_custo', 'tb_contratos'),
    ('ix_tb_localizacoes_nome', 'tb_localizacoes'),
    ('ix_tb_marcas_nome', 'tb_marcas'),
]

# Para o downgrade: (nome, tabela, colunas)
_RECRIAR = [
    ('ix_assoc_user_contrato_user_id', 'tb_associacao_user_contrato', ['user_id']),
    ('ix_cessoes_cedido_por_id', 'tb_cessoes', ['cedido_por_id']),
    ('ix_solicitacoes_solicitante_id', 'tb_solicitacoes', ['solicitante_id']),
    ('ix_solicitacoes_status', 'tb_solicitacoes', ['status']),
    ('ix_tb_audit_log_id', 'tb_audit_log', ['id']),
    ('ix_tb_cessoes_id', 'tb_cessoes', ['id']),
    ('ix_tb_eletronicos_id', 'tb_eletronicos', ['id']),
    ('ix_tb_users_id', 'tb_users', ['id']),
    ('ix_tb_contratos_centro_custo', 'tb_contratos', ['centro_custo']),
    ('ix_tb_localizacoes_nome', 'tb_localizacoes', ['nome']),
    ('ix_tb_marcas_nome', 'tb_marcas', ['nome']),
]


def upgrade() -> None:
    for nome, tabela in _REDUNDANTES:
        op.execute(f'DROP INDEX IF EXISTS {nome}')
        del tabela  # nome do índice é global no schema; tabela é só doc


def downgrade() -> None:
    for nome, tabela, cols in _RECRIAR:
        op.create_index(nome, tabela, cols)
