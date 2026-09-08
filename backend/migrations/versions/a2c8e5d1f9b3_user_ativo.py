"""Marca de acesso: tb_users.ativo

Espelha o grupo do Keycloak dentro do sistema. Quem perde o acesso fica
`ativo = false` — a linha NAO e removida, porque ha FKs de
tb_associacao_user_contrato, tb_associacao_user_eletronico, tb_solicitacoes,
tb_cessoes e tb_audit_log apontando para ela.

Todo mundo que ja existe entra como ativo: a coluna nasce com default true, e
quem tiver perdido o acesso sera marcado na primeira requisicao que fizer.

Revision ID: a2c8e5d1f9b3
Revises: f9b2d6e4a1c7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a2c8e5d1f9b3'
down_revision: Union[str, Sequence[str], None] = 'f9b2d6e4a1c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tb_users',
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('tb_users', 'ativo')
