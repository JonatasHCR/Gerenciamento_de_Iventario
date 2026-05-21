from typing import Literal

from pydantic import BaseModel, Field

StatusEletronico = Literal['Interno', 'Externo', 'Em Manutenção']


class EletronicoCreate(BaseModel):
    numero_serie: str = Field(..., description='Número de série do eletrônico')
    numero_patrimonio: str = Field(
        ..., description='Número de patrimônio do eletrônico'
    )
    nome: str = Field(..., description='Nome do eletrônico')
    marca: str | None = Field(None, description='Marca do eletrônico')
    modelo: str | None = Field(None, description='Modelo do eletrônico')
    # Validado contra o catálogo dinâmico tb_tipos_eletronico no service.
    tipo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description='Tipo do eletrônico (deve existir em /tipos-eletronico/)',
    )
    status: StatusEletronico = Field(
        ..., description='Status do eletrônico'
    )
    ip: str | None = Field(None, description='Endereço IP do eletrônico')
    localizacao: str | None = Field(
        None, description='Localização do eletrônico'
    )
    descricao: str | None = Field(None, description='Descrição do eletrônico')
    centro_custo: str = Field(
        ...,
        description='Centro de custo que o eletrônico está associado',
    )


class EletronicoRead(EletronicoCreate):
    id: int = Field(..., description='ID do eletrônico')


class EletronicoList(BaseModel):
    eletronicos: list[EletronicoRead] = Field(
        ..., description='Lista de eletrônicos'
    )
    total: int = Field(..., description='Total de registros (sem paginação)')
    page: int = Field(..., description='Página atual')
    page_size: int = Field(..., description='Itens por página')
    pages: int = Field(..., description='Total de páginas')
