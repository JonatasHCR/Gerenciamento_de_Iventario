from datetime import datetime

from pydantic import BaseModel, Field


class MarcaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)


class MarcaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)


class MarcaRead(BaseModel):
    id: int
    nome: str
    criado_em: datetime

    model_config = {'from_attributes': True}


class MarcaList(BaseModel):
    marcas: list[MarcaRead]
