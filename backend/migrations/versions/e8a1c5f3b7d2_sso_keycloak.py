"""SSO via Keycloak: senha deixa de ser obrigatória, entra o external_id

A autenticação saiu deste serviço. `senha` fica nula porque nenhum hash legado
foi migrado — o reset é forçado e cada pessoa define a sua no primeiro acesso.
`external_id` guarda o `sub` do Keycloak (UUID) e passa a ser o vínculo estável
entre a conta local e a identidade.

A coluna `senha` NÃO é derrubada: linhas antigas continuam com o hash até que se
decida limpá-las, e mantê-la torna esta migration reversível sem perda.

Nada toca na PK — há FKs de tb_associacao_user_contrato,
tb_associacao_user_eletronico, tb_solicitacoes, tb_cessoes e tb_audit_log
apontando para tb_users.id. É justamente por isso que o casamento inicial é por
email: preserva o id de quem já tinha conta.

Revision ID: e8a1c5f3b7d2
Revises: d4e7b2a9c6f3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e8a1c5f3b7d2'
down_revision: Union[str, Sequence[str], None] = 'd4e7b2a9c6f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'tb_users',
        'senha',
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column(
        'tb_users',
        sa.Column('external_id', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_tb_users_external_id', 'tb_users', ['external_id'], unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_tb_users_external_id', table_name='tb_users')
    op.drop_column('tb_users', 'external_id')

    # Voltar `senha` a NOT NULL só é possível se nenhuma linha estiver nula — e
    # estarão, para todo mundo provisionado pelo SSO. Preenche com string vazia,
    # que não é hash válido de nenhum esquema e portanto não autentica ninguém.
    op.execute("UPDATE tb_users SET senha = '' WHERE senha IS NULL")
    op.alter_column(
        'tb_users',
        'senha',
        existing_type=sa.String(length=255),
        nullable=False,
    )
