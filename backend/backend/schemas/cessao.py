from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.eletronicos import EletronicoRead


class PerifericoItem(BaseModel):
    """Periférico avulso (sem patrimônio) — só consta no termo."""

    nome: str = Field(..., min_length=1, max_length=255)
    quantidade: int = Field(1, ge=1)


class CessaoCreate(BaseModel):
    eletronico_ids: list[int] = Field(..., min_length=1)
    responsavel: str = Field(..., min_length=1)
    centro_custo_destino: str = Field(..., min_length=1)
    cedido_em: datetime | None = Field(
        None, description='Data da cessão. Se omitido, usa o momento atual.'
    )
    perifericos: list[PerifericoItem] = Field(
        default_factory=list,
        description='Periféricos avulsos (mouse, teclado, kit…) só p/ termo.',
    )


class CessaoDevolverRequest(BaseModel):
    eletronico_ids: list[int] = Field(
        ...,
        min_length=1,
        description='IDs dos equipamentos devolvidos nesta operação.',
    )
    devolvida_em: datetime | None = Field(
        None, description='Data da devolução. Se omitido, usa o momento atual.'
    )


class EletronicoCessaoRead(EletronicoRead):
    devolvido_em: datetime | None = None
    devolvida_por_id: int | None = None
    devolucao_lote: int | None = None


class DevolucaoRead(BaseModel):
    lote: int
    devolvida_em: datetime
    devolvida_por_id: int | None = None
    gestor_visto_em: datetime | None = None
    eletronicos: list[EletronicoRead] = []


class RecebimentoPendenteItem(BaseModel):
    cessao_id: int
    lote: int
    devolvida_em: datetime
    devolvida_por_id: int | None = None


class RecebimentosPendentesGestor(BaseModel):
    count: int
    items: list[RecebimentoPendenteItem] = []


class MarcarVistosResponse(BaseModel):
    marcadas: int


class CessaoRead(BaseModel):
    id: int
    responsavel: str
    centro_custo_destino: str
    cedido_em: datetime
    cedido_por_id: int | None = None
    devolvida_em: datetime | None = None
    devolvida_por_id: int | None = None
    status: Literal['ativa', 'parcial', 'devolvida']
    total_eletronicos: int
    total_devolvidos: int
    total_pendentes: int
    eletronicos: list[EletronicoCessaoRead] = []
    devolucoes: list[DevolucaoRead] = []
    perifericos: list[PerifericoItem] = []

    model_config = {'from_attributes': True}


class CessaoList(BaseModel):
    cessoes: list[CessaoRead]
