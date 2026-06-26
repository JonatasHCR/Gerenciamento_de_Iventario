"""remove índices duplicados em tb_eletronicos

`centro_custo` e `status` estavam indexados duas vezes: o schema inicial
criou ix_eletronicos_{centro_custo,status,tipo} e a migration
f4b2d7a9c3e1 recriou centro_custo/status como ix_tb_eletronicos_*. Os
duplicados só oneram escrita/armazenamento. Mantém um índice por coluna
e alinha o nome do índice de `tipo` ao padrão do model (index=True).

Revision ID: c8f1a4d7e2b3
Revises: b6e9c3f2a8d1
Create Date: 2026-06-26 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c8f1a4d7e2b3'
down_revision: Union[str, Sequence[str], None] = 'b6e9c3f2a8d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Duplicados de centro_custo e status (mantém ix_tb_eletronicos_*)
    op.drop_index(
        'ix_eletronicos_centro_custo', table_name='tb_eletronicos'
    )
    op.drop_index('ix_eletronicos_status', table_name='tb_eletronicos')
    # tipo: mantém o índice, só renomeia para o padrão do model
    op.execute(
        'ALTER INDEX ix_eletronicos_tipo '
        'RENAME TO ix_tb_eletronicos_tipo'
    )


def downgrade() -> None:
    op.execute(
        'ALTER INDEX ix_tb_eletronicos_tipo '
        'RENAME TO ix_eletronicos_tipo'
    )
    op.create_index(
        'ix_eletronicos_status', 'tb_eletronicos', ['status']
    )
    op.create_index(
        'ix_eletronicos_centro_custo',
        'tb_eletronicos',
        ['centro_custo'],
    )
