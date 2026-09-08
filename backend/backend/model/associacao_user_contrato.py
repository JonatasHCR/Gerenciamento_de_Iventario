from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
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

    # Quem criou este vínculo. O sync só mexe nas linhas 'receita'; 'local'
    # continua sendo cadastro pela UI (Funcionario, Subgestor) e é intocado.
    # Sem esta coluna, o sync apagaria vínculos feitos à mão.
    origem = Column(String(10), nullable=False, server_default='local', default='local')

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
        CheckConstraint(
            "origem IN ('local', 'receita')",
            name='check_origem_valid',
        ),
        # user_id é 2ª coluna da PK composta (centro_custo, user_id).
        # get_user_context() filtra só por user_id em toda requisição.
        Index('ix_assoc_contrato_user_id', 'user_id'),
    )
