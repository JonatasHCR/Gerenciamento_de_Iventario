"""tabela tb_localizacoes

Revision ID: a1f8c4d9b372
Revises: 8b33ec3fe9f3
Create Date: 2026-05-20 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1f8c4d9b372'
down_revision: Union[str, Sequence[str], None] = '8b33ec3fe9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tb_localizacoes',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome', name='uq_localizacoes_nome'),
    )
    op.create_index(
        op.f('ix_tb_localizacoes_nome'),
        'tb_localizacoes',
        ['nome'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_tb_localizacoes_nome'),
        table_name='tb_localizacoes',
    )
    op.drop_table('tb_localizacoes')
