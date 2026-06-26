from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Modelo(Base):
    """
    Catálogo de modelos, sempre **associado a uma marca**
    (Latitude 5420 → Dell, EliteBook 840 → HP, …).

    - Qualquer usuário autenticado pode criar (inline no form de
      cadastro de equipamento).
    - Apenas Admin pode editar/excluir via /modelos.

    O `Eletronico.modelo` continua sendo uma string — a relação é por
    nome (cascade rename no service). O nome do modelo é único **por
    marca** (a mesma string pode existir em marcas diferentes).
    """

    __tablename__ = 'tb_modelos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, index=True)
    # Text (igual ao Eletronico.descricao) — multilinha, sem limite rígido.
    descricao = Column(Text, nullable=True)
    marca_id = Column(
        Integer,
        ForeignKey('tb_marcas.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )

    marca = relationship('Marca', lazy='joined')

    __table_args__ = (
        UniqueConstraint('marca_id', 'nome', name='uq_modelo_marca_nome'),
    )

    @property
    def marca_nome(self) -> str | None:
        """Nome da marca — usado pelo ModeloRead (from_attributes)."""
        return self.marca.nome if self.marca else None
