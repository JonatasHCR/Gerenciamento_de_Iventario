from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Marca(Base):
    """
    Catálogo de marcas de equipamentos (Dell, HP, Samsung, …).

    - Qualquer usuário autenticado pode criar (inline no form de
      cadastro de equipamento).
    - Apenas Admin pode editar/excluir via /marcas.

    O `Eletronico.marca` continua sendo uma string — a relação com esse
    catálogo é por nome (cascade rename no service), igual a
    Localizacao/TipoEletronico.
    """

    __tablename__ = 'tb_marcas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(
        String(100), unique=True, nullable=False, index=True
    )
    # Sem descrição: a descrição é do modelo, não da marca.
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
