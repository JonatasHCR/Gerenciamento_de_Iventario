from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    Text,
)

from backend.core.database import Base


class Contrato(Base):
    __tablename__ = 'tb_contratos'
    __comment__ = 'Centros de custo — sincronizados da receita, que é a dona'

    # String(20), não String(4): `cost_centers.cr_code` na receita é string sem
    # limite. Hoje todos têm 4 caracteres, mas nada impede um CC novo mais
    # longo (os specs de lá usam 'CASC-1', 'MVREQ-1') — e aí o sync quebraria
    # em silêncio. As FKs são ON UPDATE CASCADE, então alargar é indolor.
    centro_custo = Column(String(20), primary_key=True)
    descricao = Column(String(255), nullable=False)

    # --- Campos sincronizados da receita -----------------------------------
    # Preenchidos por service/sync_receita.py. Não editar pela UI: o próximo
    # ciclo de sincronização sobrescreve.
    cliente_nome = Column(String(255), nullable=True)
    cliente_full_name = Column(String(255), nullable=True)

    # O texto completo do `coordinator` da receita, como veio. Guardado além do
    # vínculo em tb_associacao_user_contrato porque a receita admite coordenador
    # que NÃO tem conta aqui — sem este campo, esses nomes sumiriam da tela.
    gestor_nomes = Column(Text, nullable=True)

    # CC apagado na receita vira ativo=false, nunca DELETE: há FKs de
    # tb_eletronicos, tb_cessoes e tb_solicitacoes apontando para cá. Some da
    # UI de cadastro novo, continua legível no histórico.
    ativo = Column(Boolean, nullable=False, server_default='true', default=True)

    sincronizado_em = Column(DateTime(timezone=True), nullable=True)
