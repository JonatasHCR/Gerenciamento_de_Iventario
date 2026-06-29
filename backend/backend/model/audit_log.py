from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """
    Registro de ações relevantes (aprovações, exclusões, criações de
    cessão, etc.) para rastreabilidade. Append-only; nunca atualizado
    nem deletado pela aplicação.
    """

    __tablename__ = 'tb_audit_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Ex.: 'solicitacao.aprovar', 'cessao.delete', 'user.delete'
    action = Column(String(50), nullable=False, index=True)
    # Quem fez a ação — preservado mesmo se o usuário for excluído depois.
    user_id = Column(
        Integer,
        ForeignKey('tb_users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    # Tipo do recurso afetado: 'solicitacao', 'cessao', 'user', 'eletronico'
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    # Snapshot dos campos relevantes na hora da ação.
    payload = Column(JSON, nullable=True)
    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )
