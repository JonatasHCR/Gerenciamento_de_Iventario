from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)

from backend.core.database import Base


class Eletronico(Base):
    __tablename__ = 'tb_eletronicos'
    __comment__ = 'Tabela de eletrônicos do sistema'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero_serie = Column(String(100), nullable=False, unique=True)
    numero_patrimonio = Column(String(100), nullable=False, unique=True)
    nome = Column(String(255), nullable=False)
    marca = Column(String(100))
    tipo = Column(String(100), nullable=False)
    modelo = Column(String(100))
    status = Column(String(50), nullable=False, index=True)
    ip = Column(String(15))
    localizacao = Column(String(255))
    descricao = Column(Text)
    centro_custo = Column(String(4), nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_eletronico_centro_custo',
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
        CheckConstraint(
            "status IN ('Interno', 'Externo', 'Em Manutenção')",
            name='check_status_valid',
        ),
        # CHECK do `tipo` foi removido — validação agora é via catálogo
        # dinâmico tb_tipos_eletronico (ver migration f7b2d4a8e3c1 e
        # backend/service/tipo_eletronico.py:assert_nome_valido).
    )
