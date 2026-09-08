from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String

from backend.core.database import Base


class User(Base):
    __tablename__ = 'tb_users'
    __comment__ = 'Tabela de usuários do sistema'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)

    # Nulo desde que a autenticação passou ao Keycloak. A coluna continua
    # existindo para não quebrar linhas antigas, mas nada mais a lê nem a
    # escreve — nenhum hash legado foi migrado, o reset foi forçado.
    senha = Column(String(255), nullable=True)

    # `tipo` é o PAPEL dentro do sistema e continua local: o inventário o muta
    # por regra própria (aprovação de solicitação de cargo). O grupo do
    # Keycloak diz apenas se a pessoa pode ENTRAR.
    tipo = Column(String(50), nullable=False)

    # O `sub` do Keycloak (UUID). É o vínculo estável entre a conta local e a
    # identidade: no primeiro login o usuário é achado por email e este campo é
    # gravado; daí em diante o casamento é por aqui.
    external_id = Column(String(64), nullable=True, unique=True, index=True)

    # Espelha o acesso concedido no Keycloak.
    #
    # Vira False quando a pessoa perde o grupo `/apps/inventario` — a conta NÃO
    # é apagada, porque há eletrônicos, cessões, solicitações, associações de
    # centro de custo e registros de auditoria apontando para ela. Volta a True
    # se o acesso for devolvido.
    #
    # Não confundir com `tipo`: aquilo é o PAPEL (o que pode fazer), isto é o
    # ACESSO (se pode entrar). Perder o acesso não rebaixa o papel — quem for
    # readmitido volta como era.
    ativo = Column(Boolean, nullable=False, server_default='true', default=True)

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('Admin', 'Funcionario', 'Gestor', "
            "'Subgestor', 'Tecnico_TI' )",
            name='check_tipo_valid',
        ),
    )
