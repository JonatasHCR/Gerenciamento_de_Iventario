from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _now_sp() -> datetime:
    return datetime.now(tz=ZoneInfo('America/Sao_Paulo'))


class Cessao(Base):
    __tablename__ = 'tb_cessoes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    responsavel = Column(String(255), nullable=False)
    centro_custo_destino = Column(String(4), nullable=False)
    cedido_em = Column(  # noqa: E501
        DateTime(timezone=True), nullable=False, default=_now_sp,
    )
    cedido_por_id = Column(
        Integer,
        ForeignKey('tb_users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    devolvida_em = Column(DateTime(timezone=True), nullable=True)
    devolvida_por_id = Column(
        Integer, ForeignKey('tb_users.id', ondelete='SET NULL'), nullable=True
    )

    eletronicos_assoc = relationship(
        'CessaoEletronico',
        back_populates='cessao',
        cascade='all, delete-orphan',
    )
    perifericos = relationship(
        'CessaoPeriferico',
        back_populates='cessao',
        cascade='all, delete-orphan',
    )


class CessaoPeriferico(Base):
    """
    Periféricos avulsos incluídos numa cessão (mouse, teclado, kit
    teclado+mouse, etc.). São digitados livremente, **não têm
    patrimônio** e **não fazem parte do controle de inventário** —
    existem só para constar no Termo de Responsabilidade.
    """

    __tablename__ = 'tb_cessao_periferico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cessao_id = Column(
        Integer,
        ForeignKey('tb_cessoes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    nome = Column(String(255), nullable=False)
    quantidade = Column(Integer, nullable=False, default=1)

    cessao = relationship('Cessao', back_populates='perifericos')


class CessaoEletronico(Base):
    __tablename__ = 'tb_cessao_eletronico'

    cessao_id = Column(
        Integer,
        ForeignKey('tb_cessoes.id', ondelete='CASCADE'),
        primary_key=True,
    )
    eletronico_id = Column(
        Integer,
        ForeignKey('tb_eletronicos.id', ondelete='CASCADE'),
        primary_key=True,
    )
    devolvido_em = Column(DateTime(timezone=True), nullable=True)
    devolvida_por_id = Column(
        Integer, ForeignKey('tb_users.id', ondelete='SET NULL'), nullable=True
    )
    devolucao_lote = Column(Integer, nullable=True)
    gestor_visto_em = Column(DateTime(timezone=True), nullable=True)

    cessao = relationship('Cessao', back_populates='eletronicos_assoc')

    __table_args__ = (
        # recebimentos_pendentes_gestor() e marcar_recebimentos_vistos()
        # filtram WHERE devolvido_em IS NOT NULL AND gestor_visto_em IS NULL.
        Index('ix_ce_devolvido_em', 'devolvido_em'),
        Index('ix_ce_gestor_visto_em', 'gestor_visto_em'),
    )
