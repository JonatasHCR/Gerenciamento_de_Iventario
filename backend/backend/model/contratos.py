from sqlalchemy import (
    Column,
    String,
)

from backend.core.database import Base


class Contrato(Base):
    __tablename__ = 'tb_contratos'
    __comment__ = 'Tabela de contratos do sistema'

    centro_custo = Column(String(4), primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
