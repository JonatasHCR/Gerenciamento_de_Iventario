from datetime import datetime

from pydantic import BaseModel, Field


class ModeloCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: str | None = None
    marca_id: int = Field(..., description='Marca à qual o modelo pertence')


class ModeloUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    descricao: str | None = None
    marca_id: int | None = Field(None, description='Nova marca do modelo')


class ModeloRead(BaseModel):
    id: int
    nome: str
    descricao: str | None = None
    marca_id: int
    marca_nome: str | None = None
    criado_em: datetime

    model_config = {'from_attributes': True}


class ModeloList(BaseModel):
    modelos: list[ModeloRead]
