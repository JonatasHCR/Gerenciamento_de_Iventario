"""tabela tb_solicitacao_periferico

Periféricos avulsos propostos numa solicitação de cessão (Subgestor →
Gestor); copiados para a Cessao real na aprovação.

Revision ID: b6e9c3f2a8d1
Revises: a2c5e8b1d4f7
Create Date: 2026-06-26 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b6e9c3f2a8d1'
down_revision: Union[str, Sequence[str], None] = 'a2c5e8b1d4f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tb_solicitacao_periferico',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('solicitacao_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column(
            'quantidade',
            sa.Integer(),
            nullable=False,
            server_default='1',
        ),
        sa.ForeignKeyConstraint(
            ['solicitacao_id'],
            ['tb_solicitacoes.id'],
            name='fk_solicitacao_periferico_solicitacao',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tb_solicitacao_periferico_solicitacao_id'),
        'tb_solicitacao_periferico',
        ['solicitacao_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_tb_solicitacao_periferico_solicitacao_id'),
        table_name='tb_solicitacao_periferico',
    )
    op.drop_table('tb_solicitacao_periferico')
