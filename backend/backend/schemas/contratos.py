from pydantic import BaseModel, Field


class ContratoCreate(BaseModel):
    centro_custo: str = Field(
        ...,
        min_length=1,
        # 20, e nao 4: acompanha tb_contratos.centro_custo, alargado porque o
        # `cr_code` da receita nao tem limite de tamanho.
        max_length=20,
        description='Centro de custo do contrato',
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

    # --- Vindos da receita -------------------------------------------------
    cliente_nome: str | None = Field(
        None, description='Cliente do contrato (sincronizado da receita)'
    )
    gestor_nomes: str | None = Field(
        None,
        description=(
            'Coordenadores como a receita os registra. Pode citar gente que '
            'não tem conta no inventário — por isso é texto, além do vínculo.'
        ),
    )
    ativo: bool = Field(
        True,
        description='False quando o CC foi removido na receita. Some do '
        'cadastro novo, continua legível no histórico.',
    )
    sincronizado: bool = Field(
        False,
        description='True se o CC vem da receita. Nesse caso é somente-leitura '
        'aqui: o próximo ciclo de sincronização sobrescreveria a edição.',
    )


class ContratoList(BaseModel):
    contratos: list[ContratoRead] = Field(
        ..., description='Lista de contratos'
    )
