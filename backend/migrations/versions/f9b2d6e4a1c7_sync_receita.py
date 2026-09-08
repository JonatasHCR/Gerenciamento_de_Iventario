"""Sincronização de centros de custo com a receita

Três passos, nesta ordem — a ordem importa:

1. **Alargar `String(4)` → `String(20)`** nas cinco colunas de centro de custo.
   `cost_centers.cr_code` na receita é string SEM limite; hoje todos os valores
   reais têm 4 caracteres, mas nada impede um CC novo mais longo (os specs de lá
   usam 'CASC-1', 'MVREQ-1') e aí o primeiro sync quebraria. As FKs já são
   ON UPDATE CASCADE, então alargar é indolor. Precisa vir ANTES de qualquer
   sincronização.

2. **Campos sincronizados em `tb_contratos`** — cliente, gestores, `ativo` e a
   marca d'água.

3. **`origem` em `tb_associacao_user_contrato`** — separa o que o sync gerencia
   do que foi cadastrado à mão. Sem ela o sync apagaria vínculos locais.

Revision ID: f9b2d6e4a1c7
Revises: e8a1c5f3b7d2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f9b2d6e4a1c7'
down_revision: Union[str, Sequence[str], None] = 'e8a1c5f3b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tabela, coluna, nullable) — as cinco colunas que referenciam centro de custo.
COLUNAS_CC = [
    ('tb_contratos', 'centro_custo', False),
    ('tb_eletronicos', 'centro_custo', False),
    ('tb_cessoes', 'centro_custo_destino', False),
    ('tb_solicitacoes', 'centro_custo', True),
    ('tb_solicitacoes', 'centro_custo_destino', True),
]


def upgrade() -> None:
    # 1) alargamento. A PK de tb_contratos vem primeiro; as FKs com
    #    ON UPDATE CASCADE acompanham sem precisar ser derrubadas.
    for tabela, coluna, anulavel in COLUNAS_CC:
        op.alter_column(
            tabela,
            coluna,
            existing_type=sa.String(length=4),
            type_=sa.String(length=20),
            existing_nullable=anulavel,
        )

    # 2) campos que a receita passa a preencher
    op.add_column('tb_contratos', sa.Column('cliente_nome', sa.String(length=255), nullable=True))
    op.add_column('tb_contratos', sa.Column('cliente_full_name', sa.String(length=255), nullable=True))
    op.add_column('tb_contratos', sa.Column('gestor_nomes', sa.Text(), nullable=True))
    op.add_column(
        'tb_contratos',
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'tb_contratos',
        sa.Column('sincronizado_em', sa.DateTime(timezone=True), nullable=True),
    )
    # A UI de cadastro filtra por ativo; sem índice isso vira seq scan.
    op.create_index('ix_tb_contratos_ativo', 'tb_contratos', ['ativo'])

    # 3) procedência do vínculo
    op.add_column(
        'tb_associacao_user_contrato',
        sa.Column('origem', sa.String(length=10), nullable=False, server_default='local'),
    )
    op.create_check_constraint(
        'check_origem_valid',
        'tb_associacao_user_contrato',
        "origem IN ('local', 'receita')",
    )


def downgrade() -> None:
    op.drop_constraint('check_origem_valid', 'tb_associacao_user_contrato', type_='check')
    op.drop_column('tb_associacao_user_contrato', 'origem')

    op.drop_index('ix_tb_contratos_ativo', table_name='tb_contratos')
    for coluna in ('sincronizado_em', 'ativo', 'gestor_nomes',
                   'cliente_full_name', 'cliente_nome'):
        op.drop_column('tb_contratos', coluna)

    # Estreitar de volta só é seguro se nenhum valor passar de 4 caracteres —
    # e passará, se algum CC longo já tiver sido sincronizado. Truncar seria
    # perda silenciosa de dado, então preferimos falhar alto.
    for tabela, coluna, _ in COLUNAS_CC:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM {tabela} WHERE length({coluna}) > 4) THEN
                RAISE EXCEPTION
                  'Ha valores de {tabela}.{coluna} com mais de 4 caracteres. '
                  'Estreitar a coluna truncaria dados — resolva-os antes.';
              END IF;
            END $$;
            """
        )
    for tabela, coluna, anulavel in reversed(COLUNAS_CC):
        op.alter_column(
            tabela,
            coluna,
            existing_type=sa.String(length=20),
            type_=sa.String(length=4),
            existing_nullable=anulavel,
        )
