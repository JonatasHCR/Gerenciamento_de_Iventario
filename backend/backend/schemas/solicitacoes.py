from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.cessao import PerifericoItem
from backend.schemas.eletronicos import EletronicoRead


class SolicitacaoEntradaCCCreate(BaseModel):
    centro_custo: str = Field(..., description='Centro de custo alvo')
    ocupacao_solicitada: Literal[
        'Gestor', 'Subgestor', 'Funcionario'
    ] = Field(..., description='Cargo desejado no CC')


class SolicitacaoConviteCCCreate(BaseModel):
    solicitante_id: int = Field(..., description='ID do usuário convidado')
    centro_custo: str = Field(..., description='Centro de custo')
    ocupacao_solicitada: Literal[
        'Gestor', 'Subgestor', 'Funcionario'
    ] = Field(..., description='Cargo oferecido no CC')


class SolicitacaoCargoInicialCreate(BaseModel):
    cargo_solicitado: Literal['Gestor', 'Subgestor', 'Tecnico_TI'] = Field(
        ..., description='Cargo acima de Funcionario solicitado ao Admin'
    )


class SolicitacaoCessaoCreate(BaseModel):
    eletronico_ids: list[int] = Field(..., min_length=1)
    responsavel: str = Field(
        ..., min_length=1, description='Responsável que receberá os itens'
    )
    centro_custo_destino: str = Field(
        ..., min_length=1, description='CC destino da cessão'
    )
    perifericos: list[PerifericoItem] = Field(
        default_factory=list,
        description='Periféricos avulsos (mouse, teclado, kit…) só p/ termo.',
    )


class SolicitacaoRead(BaseModel):
    id: int
    tipo: Literal['entrada_cc', 'cargo_inicial', 'cessao']
    status: Literal['pendente', 'aprovada', 'rejeitada', 'cancelada']
    solicitante_id: int
    centro_custo: str | None = None
    ocupacao_solicitada: str | None = None
    convidado_por_id: int | None = None
    cargo_solicitado: str | None = None
    centro_custo_destino: str | None = None
    responsavel: str | None = None
    eletronicos: list[EletronicoRead] = []
    perifericos: list[PerifericoItem] = []
    criado_em: datetime

    model_config = {'from_attributes': True}


class SolicitacaoList(BaseModel):
    solicitacoes: list[SolicitacaoRead]
