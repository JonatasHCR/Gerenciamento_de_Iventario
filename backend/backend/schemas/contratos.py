from pydantic import BaseModel, Field


class ContratoCreate(BaseModel):
    centro_custo: str = Field(..., description='Centro de custo do contrato')
    descricao: str = Field(
        ...,
        description='Descrição do contrato',
    )


class ContratoRead(ContratoCreate):
    pass


class ContratoList(BaseModel):
    contratos: list[ContratoRead] = Field(
        ..., description='Lista de contratos'
    )
