"""tb_modelos.descricao para TEXT (multilinha, sem limite)

Alinha a descrição do modelo ao Eletronico.descricao (Text), permitindo
descrições multilinha e longas.

Revision ID: a2c5e8b1d4f7
Revises: f1b8d4e6a9c2
Create Date: 2026-06-26 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a2c5e8b1d4f7'
down_revision: Union[str, Sequence[str], None] = 'f1b8d4e6a9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'tb_modelos',
        'descricao',
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'tb_modelos',
        'descricao',
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
