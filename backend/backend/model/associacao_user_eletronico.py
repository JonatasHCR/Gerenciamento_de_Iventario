from sqlalchemy import Column, ForeignKeyConstraint, Index, Integer

from backend.core.database import Base


class AssociacaoUserEletronico(Base):
    __tablename__ = 'tb_associacao_user_eletronico'
    __comment__ = 'Tabela de associação entre usuários e eletronicos'

    user_id = Column(Integer, primary_key=True, nullable=False)
    eletronico_id = Column(Integer, primary_key=True, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ['eletronico_id'],
            ['tb_eletronicos.id'],
            name='fk_associacao_eletronico_id',
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
        # eletronico_id é 2ª coluna da PK (user_id, eletronico_id).
        # _base_query() filtra por eletronico_id.in_(...) para Funcionários.
        Index('ix_assoc_eletronico_eletronico_id', 'eletronico_id'),
    )
