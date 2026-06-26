from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.eletronicos import Eletronico
from backend.model.marca import Marca
from backend.model.modelo import Modelo
from backend.schemas.modelo import ModeloCreate, ModeloUpdate
from backend.security.dependencies import UserContext


class ModeloService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(
        self, ctx: UserContext, *, marca_id: int | None = None
    ) -> list[Modelo]:
        del ctx  # leitura aberta a qualquer autenticado
        query = select(Modelo)
        if marca_id is not None:
            query = query.where(Modelo.marca_id == marca_id)
        query = query.order_by(Modelo.nome)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def _get_by_id(self, modelo_id: int) -> Modelo:
        result = await self.session.execute(
            select(Modelo).where(Modelo.id == modelo_id)
        )
        modelo = result.scalar_one_or_none()
        if modelo is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Modelo não encontrado.',
            )
        return modelo

    async def _assert_marca_existe(self, marca_id: int) -> None:
        existe = await self.session.scalar(
            select(Marca.id).where(Marca.id == marca_id)
        )
        if existe is None:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail='Marca informada não existe.',
            )

    async def create(
        self, data: ModeloCreate, ctx: UserContext
    ) -> Modelo:
        """Qualquer usuário autenticado pode criar modelo."""
        del ctx
        await self._assert_marca_existe(data.marca_id)
        novo = Modelo(
            nome=data.nome.strip(),
            descricao=data.descricao,
            marca_id=data.marca_id,
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
                detail='Já existe um modelo com esse nome nessa marca.',
            )

    async def update(
        self,
        modelo_id: int,
        data: ModeloUpdate,
        ctx: UserContext,
    ) -> Modelo:
        """Apenas Admin pode editar."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode editar modelos.',
            )
        modelo = await self._get_by_id(modelo_id)
        nome_antigo = modelo.nome
        payload = data.model_dump(exclude_unset=True)
        if 'nome' in payload:
            payload['nome'] = payload['nome'].strip()
        if 'marca_id' in payload:
            await self._assert_marca_existe(payload['marca_id'])

        try:
            for k, v in payload.items():
                setattr(modelo, k, v)

            # Cascade rename no campo `modelo` dos eletrônicos
            if (
                'nome' in payload
                and payload['nome'] != nome_antigo
            ):
                await self.session.execute(
                    sa_update(Eletronico)
                    .where(Eletronico.modelo == nome_antigo)
                    .values(modelo=payload['nome'])
                    .execution_options(synchronize_session='fetch')
                )

            await self.session.commit()
            await self.session.refresh(modelo)
            return modelo
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um modelo com esse nome nessa marca.',
            )

    async def delete(
        self, modelo_id: int, ctx: UserContext
    ) -> Modelo:
        """Apenas Admin pode excluir."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode remover modelos.',
            )
        modelo = await self._get_by_id(modelo_id)
        await self.session.delete(modelo)
        await self.session.commit()
        return modelo
