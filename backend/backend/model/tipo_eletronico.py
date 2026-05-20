from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TipoEletronico(Base):
    """
    Catálogo dinâmico de tipos de equipamento (Computador, Notbook,
    Monitor, Tablet, Trena Digital, …). Gerenciado pelo Admin via UI.
    O `Eletronico.tipo` ainda é uma string — a validação contra esse
    catálogo é feita no service layer.
    """

    __tablename__ = 'tb_tipos_eletronico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(
        String(50), unique=True, nullable=False, index=True
    )
    descricao = Column(String(255), nullable=True)
    # Soft-delete: desativar mantém o histórico de equipamentos sem
    # quebrar referência por string.
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
