from datetime import datetime

from pydantic import BaseModel, Field


class LocalizacaoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: str | None = Field(None, max_length=255)


class LocalizacaoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    descricao: str | None = Field(None, max_length=255)


class LocalizacaoRead(BaseModel):
    id: int
    nome: str
    descricao: str | None = None
    criado_em: datetime

    model_config = {'from_attributes': True}


class LocalizacaoList(BaseModel):
    localizacoes: list[LocalizacaoRead]
