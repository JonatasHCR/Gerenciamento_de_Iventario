from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Integer,
    String,
)

from backend.core.database import Base


class AssociacaoUserContrato(Base):
    __tablename__ = 'tb_associacao_user_contrato'
    __comment__ = 'Tabela de associação entre usuários e contratos'

    centro_custo = Column(String, primary_key=True, nullable=False)
    user_id = Column(Integer, primary_key=True, nullable=False)
    ocupacao = Column(String(100), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ['centro_custo'],
            ['tb_contratos.centro_custo'],
            name='fk_associacao_centro_custo',
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
        ForeignKeyConstraint(
            ['user_id'],
            ['tb_users.id'],
            name='fk_associacao_user_id',
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
        CheckConstraint(
            "ocupacao IN ('Gestor', 'Funcionario','Subgestor')",
            name='check_ocupacao_valid',
        ),
    )
