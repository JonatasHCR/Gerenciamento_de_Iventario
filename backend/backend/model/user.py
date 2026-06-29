from sqlalchemy import CheckConstraint, Column, Integer, String

from backend.core.database import Base


class User(Base):
    __tablename__ = 'tb_users'
    __comment__ = 'Tabela de usuários do sistema'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    senha = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('Admin', 'Funcionario', 'Gestor', "
            "'Subgestor', 'Tecnico_TI' )",
            name='check_tipo_valid',
        ),
    )
