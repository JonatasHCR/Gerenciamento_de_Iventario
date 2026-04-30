from pydantic import BaseModel, Field


class EletronicoCreate(BaseModel):
    numero_serie: str = Field(..., description='Número de série do eletrônico')
    numero_patrimonio: str = Field(
        ..., description='Número de patrimônio do eletrônico'
    )
    nome: str = Field(..., description='Nome do eletrônico')
    marca: str = Field(..., description='Marca do eletrônico')
    modelo: str = Field(..., description='Modelo do eletrônico')
    tipo: str = Field(..., description='Tipo do eletrônico')
    status: str = Field(..., description='Status do eletrônico')
    ip: str = Field(..., description='Endereço IP do eletrônico')
    localizacao: str = Field(..., description='Localização do eletrônico')
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
