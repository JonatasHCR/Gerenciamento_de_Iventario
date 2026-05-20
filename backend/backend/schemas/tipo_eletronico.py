from datetime import datetime

from pydantic import BaseModel, Field


class TipoEletronicoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50)
    descricao: str | None = Field(None, max_length=255)


class TipoEletronicoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=50)
    descricao: str | None = Field(None, max_length=255)
    ativo: bool | None = None


class TipoEletronicoRead(BaseModel):
    id: int
    nome: str
    descricao: str | None = None
    ativo: bool
    criado_em: datetime

    model_config = {'from_attributes': True}


class TipoEletronicoList(BaseModel):
    tipos: list[TipoEletronicoRead]
