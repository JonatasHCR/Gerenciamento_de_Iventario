"""add missing indexes for query performance

Adiciona índices ausentes identificados por análise das queries
mais frequentes vs. colunas sem cobertura de índice:

- tb_associacao_user_contrato.user_id  → get_user_context() em toda requisição
- tb_eletronicos.centro_custo          → _base_query() em todo GET /eletronicos/
- tb_eletronicos.status                → filtro de status em GET /eletronicos/
- tb_solicitacoes.solicitante_id       → polled a cada 5s pelo frontend
- tb_solicitacoes.(status,centro_custo)→ filtro composto mais comum
- tb_cessoes.cedido_por_id             → list_all() por usuário
- tb_cessao_eletronico.devolvido_em    → recebimentos_pendentes_gestor()
- tb_cessao_eletronico.gestor_visto_em → marcar_recebimentos_vistos()
- tb_associacao_user_eletronico.eletronico_id → _base_query() Funcionários

Revision ID: f4b2d7a9c3e1
Revises: a1f8c4d9b372
Create Date: 2026-05-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f4b2d7a9c3e1'
down_revision: Union[str, Sequence[str], None] = 'a1f8c4d9b372'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona índices para cobrir as queries mais frequentes."""

    # tb_associacao_user_contrato — user_id é 2ª coluna da PK composta
    op.create_index(
        'ix_assoc_contrato_user_id',
        'tb_associacao_user_contrato',
        ['user_id'],
    )

    # tb_eletronicos — filtros principais de visibilidade e listagem
    op.create_index(
        op.f('ix_tb_eletronicos_centro_custo'),
        'tb_eletronicos',
        ['centro_custo'],
    )
    op.create_index(
        op.f('ix_tb_eletronicos_status'),
        'tb_eletronicos',
        ['status'],
    )

    # tb_solicitacoes — polled a cada 5s; filtros mais comuns
    op.create_index(
        op.f('ix_tb_solicitacoes_solicitante_id'),
        'tb_solicitacoes',
        ['solicitante_id'],
    )
    op.create_index(
        'ix_sol_status_centro_custo',
        'tb_solicitacoes',
        ['status', 'centro_custo'],
    )

    # tb_cessoes — filtro por criador na listagem
    op.create_index(
        op.f('ix_tb_cessoes_cedido_por_id'),
        'tb_cessoes',
        ['cedido_por_id'],
    )

    # tb_cessao_eletronico — filtros IS NULL / IS NOT NULL nas notificações
    op.create_index(
        'ix_ce_devolvido_em',
        'tb_cessao_eletronico',
        ['devolvido_em'],
    )
    op.create_index(
        'ix_ce_gestor_visto_em',
        'tb_cessao_eletronico',
        ['gestor_visto_em'],
    )

    # tb_associacao_user_eletronico — eletronico_id é 2ª coluna da PK composta
    op.create_index(
        'ix_assoc_eletronico_eletronico_id',
        'tb_associacao_user_eletronico',
        ['eletronico_id'],
    )


def downgrade() -> None:
    """Remove os índices adicionados."""

    op.drop_index(
        'ix_assoc_eletronico_eletronico_id',
        table_name='tb_associacao_user_eletronico',
    )
    op.drop_index(
        'ix_ce_gestor_visto_em',
        table_name='tb_cessao_eletronico',
    )
    op.drop_index(
        'ix_ce_devolvido_em',
        table_name='tb_cessao_eletronico',
    )
    op.drop_index(
        op.f('ix_tb_cessoes_cedido_por_id'),
        table_name='tb_cessoes',
    )
    op.drop_index(
        'ix_sol_status_centro_custo',
        table_name='tb_solicitacoes',
    )
    op.drop_index(
        op.f('ix_tb_solicitacoes_solicitante_id'),
        table_name='tb_solicitacoes',
    )
    op.drop_index(
        op.f('ix_tb_eletronicos_status'),
        table_name='tb_eletronicos',
    )
    op.drop_index(
        op.f('ix_tb_eletronicos_centro_custo'),
        table_name='tb_eletronicos',
    )
    op.drop_index(
        'ix_assoc_contrato_user_id',
        table_name='tb_associacao_user_contrato',
    )
