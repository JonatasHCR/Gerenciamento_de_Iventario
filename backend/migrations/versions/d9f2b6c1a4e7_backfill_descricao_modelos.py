"""backfill da descrição dos modelos (descrição mais recente)

Preenche tb_modelos.descricao usando a descrição do equipamento **mais
recente** (maior id) de cada par marca+modelo, considerando apenas
descrições não-vazias. Só preenche modelos que ainda estão sem descrição.

Revision ID: d9f2b6c1a4e7
Revises: c7d1a3e9f2b4
Create Date: 2026-06-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd9f2b6c1a4e7'
down_revision: Union[str, Sequence[str], None] = 'c7d1a3e9f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill — descrição mais recente por marca+modelo."""
    op.execute(
        """
        UPDATE tb_modelos mo
        SET descricao = sub.descricao
        FROM (
            SELECT DISTINCT ON (TRIM(e.marca), TRIM(e.modelo))
                   TRIM(e.marca)  AS marca,
                   TRIM(e.modelo) AS modelo,
                   e.descricao    AS descricao
            FROM tb_eletronicos e
            WHERE e.modelo IS NOT NULL AND TRIM(e.modelo) <> ''
              AND e.marca  IS NOT NULL AND TRIM(e.marca)  <> ''
              AND e.descricao IS NOT NULL AND TRIM(e.descricao) <> ''
            ORDER BY TRIM(e.marca), TRIM(e.modelo), e.id DESC
        ) sub
        JOIN tb_marcas ma ON ma.nome = sub.marca
        WHERE mo.marca_id = ma.id
          AND mo.nome = sub.modelo
          AND (mo.descricao IS NULL OR TRIM(mo.descricao) = '');
        """
    )


def downgrade() -> None:
    """Sem downgrade — não há como distinguir o que foi semeado do que
    foi editado manualmente depois."""
