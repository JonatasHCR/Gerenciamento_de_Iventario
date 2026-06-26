"""backfill tb_marcas e tb_modelos a partir de tb_eletronicos

Semeia o catálogo de marcas/modelos com os valores que já existem como
texto nos equipamentos. Idempotente (ON CONFLICT DO NOTHING), então pode
rodar de novo sem duplicar. Modelos sem marca não são importados (o
catálogo de modelo exige uma marca).

Revision ID: c7d1a3e9f2b4
Revises: b5c9e2f1a8d3
Create Date: 2026-06-26 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c7d1a3e9f2b4'
down_revision: Union[str, Sequence[str], None] = 'b5c9e2f1a8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill — marcas distintas, depois modelos ligados à marca."""
    op.execute(
        """
        INSERT INTO tb_marcas (nome)
        SELECT DISTINCT TRIM(marca)
        FROM tb_eletronicos
        WHERE marca IS NOT NULL AND TRIM(marca) <> ''
        ON CONFLICT (nome) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO tb_modelos (nome, marca_id)
        SELECT DISTINCT TRIM(e.modelo), m.id
        FROM tb_eletronicos e
        JOIN tb_marcas m ON m.nome = TRIM(e.marca)
        WHERE e.modelo IS NOT NULL AND TRIM(e.modelo) <> ''
          AND e.marca IS NOT NULL AND TRIM(e.marca) <> ''
        ON CONFLICT (marca_id, nome) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Sem downgrade de dados — não há como saber o que foi semeado
    versus criado manualmente depois."""
