from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Localizacao(Base):
    """
    Catálogo de localizações onde equipamentos podem estar
    (Sala TI, Almoxarifado, Sala da Diretoria, etc.).

    - Qualquer usuário autenticado pode criar (inline no form de
      cadastro de equipamento).
    - Apenas Admin pode editar/desativar/excluir via /localizacoes.
    """

    __tablename__ = 'tb_localizacoes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # unique=True já cria índice btree em nome — sem index=True redundante.
    nome = Column(String(100), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
