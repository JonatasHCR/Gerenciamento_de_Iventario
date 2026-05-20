from pydantic import BaseModel, Field


class ContratoCreate(BaseModel):
    centro_custo: str = Field(
        ..., min_length=1, max_length=4, description='Centro de custo do contrato'
    )
    descricao: str = Field(
        ...,
        description='Descrição do contrato',
    )


class ContratoRead(ContratoCreate):
    gestor_nome: str | None = Field(
        None, description='Nome do Gestor do CC (se houver)'
    )
    total_membros: int = Field(
        0, description='Total de usuários associados ao CC'
    )


class ContratoList(BaseModel):
    contratos: list[ContratoRead] = Field(
        ..., description='Lista de contratos'
    )
