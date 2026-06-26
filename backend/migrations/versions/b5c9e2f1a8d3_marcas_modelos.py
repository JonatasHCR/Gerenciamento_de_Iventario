"""tabelas tb_marcas e tb_modelos

Revision ID: b5c9e2f1a8d3
Revises: f4b2d7a9c3e1
Create Date: 2026-06-26 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b5c9e2f1a8d3'
down_revision: Union[str, Sequence[str], None] = 'f4b2d7a9c3e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tb_marcas',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome', name='uq_marcas_nome'),
    )
    op.create_index(
        op.f('ix_tb_marcas_nome'),
        'tb_marcas',
        ['nome'],
        unique=False,
    )

    op.create_table(
        'tb_modelos',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('marca_id', sa.Integer(), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ['marca_id'],
            ['tb_marcas.id'],
            name='fk_modelo_marca',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'marca_id', 'nome', name='uq_modelo_marca_nome'
        ),
    )
    op.create_index(
        op.f('ix_tb_modelos_nome'),
        'tb_modelos',
        ['nome'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tb_modelos_marca_id'),
        'tb_modelos',
        ['marca_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_tb_modelos_marca_id'), table_name='tb_modelos'
    )
    op.drop_index(
        op.f('ix_tb_modelos_nome'), table_name='tb_modelos'
    )
    op.drop_table('tb_modelos')
    op.drop_index(
        op.f('ix_tb_marcas_nome'), table_name='tb_marcas'
    )
    op.drop_table('tb_marcas')
