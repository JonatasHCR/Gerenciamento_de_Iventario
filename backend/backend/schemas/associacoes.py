from typing import Literal

from pydantic import BaseModel, Field

# ─── AssociacaoUserContrato


class AssociacaoUserContratoCreate(BaseModel):
    user_id: int = Field(..., description='ID do usuário')
    centro_custo: str = Field(..., description='Centro de custo do contrato')
    ocupacao: Literal['Gestor', 'Subgestor', 'Funcionario'] = Field(
        ..., description='Ocupação do usuário no contrato'
    )


class AssociacaoUserContratoRead(AssociacaoUserContratoCreate):
    pass


class AssociacaoUserContratoList(BaseModel):
    associacoes: list[AssociacaoUserContratoRead] = Field(
        ..., description='Lista de associações usuário-contrato'
    )


# ─── AssociacaoUserEletronico


class AssociacaoUserEletronicoCreate(BaseModel):
    user_id: int = Field(..., description='ID do usuário')
    eletronico_id: int = Field(..., description='ID do eletrônico')


class AssociacaoUserEletronicoRead(AssociacaoUserEletronicoCreate):
    pass


class AssociacaoUserEletronicoList(BaseModel):
    associacoes: list[AssociacaoUserEletronicoRead] = Field(
        ..., description='Lista de associações usuário-eletrônico'
    )
