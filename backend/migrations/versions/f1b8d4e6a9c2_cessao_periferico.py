"""tabela tb_cessao_periferico

Periféricos avulsos (sem patrimônio, fora do controle de inventário)
incluídos numa cessão, só para constar no Termo de Responsabilidade.

Revision ID: f1b8d4e6a9c2
Revises: e3a7c8d2f5b9
Create Date: 2026-06-26 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1b8d4e6a9c2'
down_revision: Union[str, Sequence[str], None] = 'e3a7c8d2f5b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tb_cessao_periferico',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('cessao_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column(
            'quantidade',
            sa.Integer(),
            nullable=False,
            server_default='1',
        ),
        sa.ForeignKeyConstraint(
            ['cessao_id'],
            ['tb_cessoes.id'],
            name='fk_cessao_periferico_cessao',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tb_cessao_periferico_cessao_id'),
        'tb_cessao_periferico',
        ['cessao_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_tb_cessao_periferico_cessao_id'),
        table_name='tb_cessao_periferico',
    )
    op.drop_table('tb_cessao_periferico')
