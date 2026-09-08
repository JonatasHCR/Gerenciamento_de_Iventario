from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.security.dependencies import Dependencies, UserContext
from backend.service.audit_log import log as audit_log
from backend.service.manutencao import ALVOS, ErroDeManutencao, ManutencaoService

router_manutencao = APIRouter(prefix='/manutencao', tags=['manutencao'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


class BackupRead(BaseModel):
    nome: str
    bytes: int
    criado_em: datetime


class AlvoRead(BaseModel):
    chave: str
    rotulo: str
    aceita_cc: bool


class LimpezaCreate(BaseModel):
    alvo: str = Field(..., description='Chave do alvo (ver GET /manutencao/alvos)')
    centro_custo: str | None = Field(
        None, description='Limita a limpeza a um centro de custo'
    )
    confirmacao: str = Field(
        ..., description='Precisa ser exatamente LIMPAR — a operação é irreversível'
    )


class RestauracaoCreate(BaseModel):
    nome: str
    confirmacao: str = Field(
        ..., description='Precisa ser exatamente RESTAURAR — substitui os dados'
    )


class ResultadoRead(BaseModel):
    mensagem: str
    detalhes: dict[str, int] | None = None


def _so_admin(ctx: UserContext) -> None:
    """Sem tipos permitidos: só Admin passa.

    Tecnico_TI tem passe livre em eletrônicos, mas apagar o banco é outra
    categoria de poder.
    """
    ctx.assert_write()


@router_manutencao.get(
    '/backups', status_code=HTTPStatus.OK, response_model=list[BackupRead]
)
async def listar_backups(session: T_AsyncSession, ctx: T_UserContext):
    _so_admin(ctx)
    return ManutencaoService(session).listar()


@router_manutencao.post(
    '/backups', status_code=HTTPStatus.CREATED, response_model=BackupRead
)
async def gerar_backup(session: T_AsyncSession, ctx: T_UserContext):
    _so_admin(ctx)
    try:
        backup = await ManutencaoService(session).gerar_backup()
    except ErroDeManutencao as e:
        raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    audit_log(
        session,
        action='manutencao.backup',
        user_id=ctx.user.id,
        target_type='banco',
        target_id=None,
        payload={'arquivo': backup.nome, 'bytes': backup.bytes},
    )
    await session.commit()
    return backup


@router_manutencao.get('/backups/{nome}')
async def baixar_backup(nome: str, session: T_AsyncSession, ctx: T_UserContext):
    _so_admin(ctx)
    try:
        caminho = ManutencaoService(session).resolver_arquivo(nome)
    except ErroDeManutencao as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e))
    return FileResponse(
        caminho, media_type='application/octet-stream', filename=caminho.name
    )


@router_manutencao.get(
    '/alvos', status_code=HTTPStatus.OK, response_model=list[AlvoRead]
)
async def listar_alvos(ctx: T_UserContext):
    _so_admin(ctx)
    return [
        {'chave': chave, 'rotulo': cfg['rotulo'], 'aceita_cc': cfg['aceita_cc']}
        for chave, cfg in ALVOS.items()
    ]


@router_manutencao.post(
    '/limpeza', status_code=HTTPStatus.OK, response_model=ResultadoRead
)
async def limpar(
    dados: LimpezaCreate, session: T_AsyncSession, ctx: T_UserContext
):
    _so_admin(ctx)
    if dados.confirmacao != 'LIMPAR':
        raise HTTPException(
            HTTPStatus.BAD_REQUEST,
            'Digite LIMPAR para confirmar. Nada foi apagado.',
        )

    try:
        removidos = await ManutencaoService(session).limpar(
            dados.alvo, centro_custo=dados.centro_custo
        )
    except ErroDeManutencao as e:
        raise HTTPException(HTTPStatus.BAD_REQUEST, str(e))

    # Auditado DEPOIS de apagar: registrar antes deixaria a marca de algo que
    # pode não ter acontecido.
    audit_log(
        session,
        action='manutencao.limpeza',
        user_id=ctx.user.id,
        target_type='banco',
        target_id=None,
        payload={
            'alvo': dados.alvo,
            'centro_custo': dados.centro_custo,
            'removidos': removidos,
        },
    )
    await session.commit()

    total = sum(removidos.values())
    return {
        'mensagem': f'{total} registro(s) removido(s).',
        'detalhes': removidos,
    }


@router_manutencao.post(
    '/restauracao', status_code=HTTPStatus.OK, response_model=ResultadoRead
)
async def restaurar(
    dados: RestauracaoCreate, session: T_AsyncSession, ctx: T_UserContext
):
    _so_admin(ctx)
    if dados.confirmacao != 'RESTAURAR':
        raise HTTPException(
            HTTPStatus.BAD_REQUEST,
            'Digite RESTAURAR para confirmar. Nada foi alterado.',
        )

    email = ctx.user.email
    try:
        arquivo = await ManutencaoService(session).restaurar(dados.nome)
    except ErroDeManutencao as e:
        raise HTTPException(HTTPStatus.BAD_REQUEST, str(e))

    # Sem auditoria aqui: o restore acabou de substituir a própria tabela de
    # auditoria, então a linha sumiria ou ficaria órfã. Fica no log da aplicação.
    return {
        'mensagem': f'Banco restaurado a partir de {arquivo} por {email}. '
        'Recarregue a página.',
        'detalhes': None,
    }
