from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Solicitacao(Base):
    __tablename__ = 'tb_solicitacoes'
    __comment__ = 'Tabela de solicitações do sistema'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default='pendente')
    solicitante_id = Column(Integer, nullable=False)

    # Campos para entrada_cc
    centro_custo = Column(String(4), nullable=True)
    ocupacao_solicitada = Column(String(50), nullable=True)
    convidado_por_id = Column(Integer, nullable=True)

    # Campo para cargo_inicial
    cargo_solicitado = Column(String(50), nullable=True)

    # Campos para cessao (Subgestor → Gestor)
    centro_custo_destino = Column(String(4), nullable=True)
    responsavel = Column(String(255), nullable=True)

    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )

    eletronicos_assoc = relationship(
        'SolicitacaoEletronico',
        back_populates='solicitacao',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['solicitante_id'],
            ['tb_users.id'],
            name='fk_solicitacao_solicitante_id',
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_solicitacao_centro_custo',
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['convidado_por_id'],
            ['tb_users.id'],
            name='fk_solicitacao_convidado_por_id',
            ondelete='SET NULL',
        ),
        CheckConstraint(
            "tipo IN ('entrada_cc', 'cargo_inicial', 'cessao')",
            name='check_solicitacao_tipo',
        ),
        CheckConstraint(
            "status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada')",
            name='check_solicitacao_status',
        ),
        CheckConstraint(
            "ocupacao_solicitada IN ('Gestor', 'Subgestor', 'Funcionario')"
            ' OR ocupacao_solicitada IS NULL',
            name='check_solicitacao_ocupacao',
        ),
        CheckConstraint(
            "cargo_solicitado IN ('Gestor', 'Subgestor', 'Tecnico_TI')"
            ' OR cargo_solicitado IS NULL',
            name='check_solicitacao_cargo',
        ),
    )


class SolicitacaoEletronico(Base):
    __tablename__ = 'tb_solicitacao_eletronico'

    solicitacao_id = Column(
        Integer,
        ForeignKey('tb_solicitacoes.id', ondelete='CASCADE'),
        primary_key=True,
    )
    eletronico_id = Column(
        Integer,
        ForeignKey('tb_eletronicos.id', ondelete='CASCADE'),
        primary_key=True,
    )

    solicitacao = relationship(
        'Solicitacao', back_populates='eletronicos_assoc'
    )
