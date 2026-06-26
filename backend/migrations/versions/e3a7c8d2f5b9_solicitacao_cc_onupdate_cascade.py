"""ON UPDATE CASCADE no FK de centro_custo das solicitações

Permite renomear o código do CC (PK de tb_contratos) propagando para
tb_solicitacoes.centro_custo automaticamente — antes o FK só tinha
ON DELETE CASCADE, o que bloqueava o rename quando havia solicitação
referenciando o CC.

Revision ID: e3a7c8d2f5b9
Revises: d9f2b6c1a4e7
Create Date: 2026-06-26 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e3a7c8d2f5b9'
down_revision: Union[str, Sequence[str], None] = 'd9f2b6c1a4e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        'fk_solicitacao_centro_custo',
        'tb_solicitacoes',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'fk_solicitacao_centro_custo',
        'tb_solicitacoes',
        'tb_contratos',
        ['centro_custo'],
        ['centro_custo'],
        ondelete='CASCADE',
        onupdate='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_solicitacao_centro_custo',
        'tb_solicitacoes',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'fk_solicitacao_centro_custo',
        'tb_solicitacoes',
        'tb_contratos',
        ['centro_custo'],
        ['centro_custo'],
        ondelete='CASCADE',
    )
