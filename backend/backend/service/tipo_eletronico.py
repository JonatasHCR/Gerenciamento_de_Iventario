from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.eletronicos import Eletronico
from backend.model.tipo_eletronico import TipoEletronico
from backend.schemas.tipo_eletronico import (
    TipoEletronicoCreate,
    TipoEletronicoUpdate,
)
from backend.security.dependencies import UserContext


class TipoEletronicoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(
        self, ctx: UserContext, *, apenas_ativos: bool = False
    ) -> list[TipoEletronico]:
        """
        - Qualquer usuário autenticado lê (é catálogo de referência).
        - `apenas_ativos=True` esconde os desativados — útil pra
          alimentar selects de cadastro.
        """
        del ctx  # leitura aberta a todos os autenticados
        query = select(TipoEletronico)
        if apenas_ativos:
            query = query.where(TipoEletronico.ativo.is_(True))
        query = query.order_by(TipoEletronico.nome)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _get_by_id(self, tipo_id: int) -> TipoEletronico:
        result = await self.session.execute(
            select(TipoEletronico).where(TipoEletronico.id == tipo_id)
        )
        t = result.scalar_one_or_none()
        if t is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Tipo não encontrado.',
            )
        return t

    async def create(
        self, data: TipoEletronicoCreate, ctx: UserContext
    ) -> TipoEletronico:
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode criar tipos.',
            )
        novo = TipoEletronico(
            nome=data.nome.strip(),
            descricao=data.descricao,
            ativo=True,
        )
        try:
            self.session.add(novo)
            await self.session.commit()
            await self.session.refresh(novo)
            return novo
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um tipo com esse nome.',
            )

    async def update(
        self,
        tipo_id: int,
        data: TipoEletronicoUpdate,
        ctx: UserContext,
    ) -> TipoEletronico:
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode editar tipos.',
            )
        tipo = await self._get_by_id(tipo_id)
        nome_antigo = tipo.nome
        payload = data.model_dump(exclude_unset=True)
        if 'nome' in payload:
            payload['nome'] = payload['nome'].strip()

        for k, v in payload.items():
            setattr(tipo, k, v)

        # Se mudou o nome, atualiza em cascata os eletrônicos
        # (eles guardam o nome como string). `synchronize_session='fetch'`
        # invalida os objetos no identity map para refletir o novo valor.
        if (
            'nome' in payload
            and payload['nome'] != nome_antigo
        ):
            await self.session.execute(
                sa_update(Eletronico)
                .where(Eletronico.tipo == nome_antigo)
                .values(tipo=payload['nome'])
                .execution_options(synchronize_session='fetch')
            )

        try:
            await self.session.commit()
            await self.session.refresh(tipo)
            return tipo
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um tipo com esse nome.',
            )

    async def delete(
        self, tipo_id: int, ctx: UserContext
    ) -> TipoEletronico:
        """
        Soft delete (`ativo=False`) se houver eletrônicos usando esse
        tipo; remoção real caso contrário.
        """
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode remover tipos.',
            )
        tipo = await self._get_by_id(tipo_id)

        em_uso = await self.session.scalar(
            select(func.count(Eletronico.id)).where(
                Eletronico.tipo == tipo.nome
            )
        )
        if em_uso and em_uso > 0:
            tipo.ativo = False
            await self.session.commit()
            await self.session.refresh(tipo)
            return tipo

        await self.session.delete(tipo)
        await self.session.commit()
        return tipo

    async def assert_nome_valido(self, nome: str) -> None:
        """
        Helper usado por EletronicoService.create/update — falha 422
        se o tipo informado não existe ou está desativado.
        """
        result = await self.session.execute(
            select(TipoEletronico).where(
                TipoEletronico.nome == nome,
                TipoEletronico.ativo.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=(
                    f"Tipo '{nome}' inválido ou desativado. "
                    'Cadastre-o em /tipos-eletronico/ antes.'
                ),
            )
