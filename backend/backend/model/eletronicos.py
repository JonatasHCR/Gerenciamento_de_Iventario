from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Integer,
    String,
)

from backend.core.engine import Base


class Eletronico(Base):
    __tablename__ = 'tb_eletronicos'
    __comment__ = 'Tabela de eletrônicos do sistema'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero_serie = Column(String(100), nullable=False, unique=True)
    numero_patrimonio = Column(String(100), nullable=False, unique=True)
    nome = Column(String(255), nullable=False)
    marca = Column(String(100), nullable=False)
    tipo = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    ip = Column(String(15), nullable=False)
    centro_custo = Column(String(4), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_eletronico_centro_custo',
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
    )
