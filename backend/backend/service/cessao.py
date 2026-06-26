from datetime import datetime
from http import HTTPStatus
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.cessao import (
    Cessao,
    CessaoEletronico,
    CessaoPeriferico,
)
from backend.model.eletronicos import Eletronico
from backend.schemas.cessao import CessaoCreate, CessaoDevolverRequest
from backend.security.dependencies import UserContext
from backend.service.audit_log import log as audit_log


class CessaoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _itens_da_cessao(
        self, cessao_id: int
    ) -> list[tuple[CessaoEletronico, Eletronico]]:
        result = await self.session.execute(
            select(CessaoEletronico, Eletronico)
            .join(Eletronico, Eletronico.id == CessaoEletronico.eletronico_id)
            .where(CessaoEletronico.cessao_id == cessao_id)
        )
        return [(ce, el) for ce, el in result.all()]

    async def _perifericos_da_cessao(
        self, cessao_id: int
    ) -> list[CessaoPeriferico]:
        result = await self.session.execute(
            select(CessaoPeriferico)
            .where(CessaoPeriferico.cessao_id == cessao_id)
            .order_by(CessaoPeriferico.id)
        )
        return list(result.scalars().all())

    @staticmethod
    def _eletronico_to_dict(
        el: Eletronico, ce: CessaoEletronico | None = None
    ) -> dict:
        return {
            'id': el.id,
            'numero_serie': el.numero_serie,
            'numero_patrimonio': el.numero_patrimonio,
            'nome': el.nome,
            'marca': el.marca,
            'tipo': el.tipo,
            'modelo': el.modelo,
            'status': el.status,
            'ip': el.ip,
            'localizacao': el.localizacao,
            'descricao': el.descricao,
            'centro_custo': el.centro_custo,
            'devolvido_em': ce.devolvido_em if ce else None,
            'devolvida_por_id': ce.devolvida_por_id if ce else None,
            'devolucao_lote': ce.devolucao_lote if ce else None,
        }

    def _serialize(
        self,
        c: Cessao,
        itens: list[tuple[CessaoEletronico, Eletronico]],
        perifericos: list[CessaoPeriferico] | None = None,
    ) -> dict:
        total = len(itens)
        devolvidos = [(ce, el) for ce, el in itens if ce.devolvido_em]
        pendentes = total - len(devolvidos)

        if total > 0 and len(devolvidos) == total:
            status = 'devolvida'
        elif len(devolvidos) > 0:
            status = 'parcial'
        else:
            status = 'ativa'

        lotes: dict[int, dict] = {}
        for ce, el in devolvidos:
            lote = ce.devolucao_lote or 1
            if lote not in lotes:
                lotes[lote] = {
                    'lote': lote,
                    'devolvida_em': ce.devolvido_em,
                    'devolvida_por_id': ce.devolvida_por_id,
                    'gestor_visto_em': ce.gestor_visto_em,
                    'eletronicos': [],
                }
            lotes[lote]['eletronicos'].append(self._eletronico_to_dict(el))

        devolucoes = [lotes[k] for k in sorted(lotes.keys())]

        return {
            'id': c.id,
            'responsavel': c.responsavel,
            'centro_custo_destino': c.centro_custo_destino,
            'cedido_em': c.cedido_em,
            'cedido_por_id': c.cedido_por_id,
            'devolvida_em': c.devolvida_em,
            'devolvida_por_id': c.devolvida_por_id,
            'status': status,
            'total_eletronicos': total,
            'total_devolvidos': len(devolvidos),
            'total_pendentes': pendentes,
            'eletronicos': [
                self._eletronico_to_dict(el, ce) for ce, el in itens
            ],
            'devolucoes': devolucoes,
            'perifericos': [
                {'nome': p.nome, 'quantidade': p.quantidade}
                for p in (perifericos or [])
            ],
        }

    def _assert_permission(self, ctx: UserContext) -> set[str]:  # noqa: PLR6301

        is_full = ctx.is_privileged or ctx.is_tecnico_ti
        gestor_ccs = {
            cc for cc, ocup in ctx.ocupacoes.items() if ocup == 'Gestor'
        }
        if not is_full and not gestor_ccs:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Gestor, Admin ou Tecnico_TI.',
            )
        return gestor_ccs

    async def create(self, data: CessaoCreate, ctx: UserContext) -> dict:
        gestor_ccs = self._assert_permission(ctx)
        is_full = ctx.is_privileged or ctx.is_tecnico_ti

        result = await self.session.execute(
            select(Eletronico).where(
                Eletronico.id.in_(data.eletronico_ids)
            )
        )
        eletronicos = list(result.scalars().all())

        encontrados = {e.id for e in eletronicos}
        faltando = set(data.eletronico_ids) - encontrados
        if faltando:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f'Eletrônicos não encontrados: {sorted(faltando)}',
            )

        if not is_full:
            for e in eletronicos:
                if e.centro_custo not in gestor_ccs:
                    raise HTTPException(
                        status_code=HTTPStatus.FORBIDDEN,
                        detail=(
                            f'Sem permissão para ceder o eletrônico '
                            f'{e.id} (CC {e.centro_custo}).'
                        ),
                    )

        for e in eletronicos:
            if e.status == 'Externo':
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=(
                        f'Eletrônico {e.id} já está cedido (Externo).'
                    ),
                )

        cessao = Cessao(
            responsavel=data.responsavel,
            centro_custo_destino=data.centro_custo_destino,
            cedido_por_id=ctx.user.id,
            cedido_em=data.cedido_em
            or datetime.now(tz=ZoneInfo('America/Sao_Paulo')),
        )
        self.session.add(cessao)
        await self.session.flush()

        for e in eletronicos:
            e.status = 'Externo'
            e.localizacao = f'Cedido para CC {data.centro_custo_destino}'
            self.session.add(
                CessaoEletronico(
                    cessao_id=cessao.id,
                    eletronico_id=e.id,
                )
            )

        for p in data.perifericos:
            self.session.add(
                CessaoPeriferico(
                    cessao_id=cessao.id,
                    nome=p.nome.strip(),
                    quantidade=p.quantidade,
                )
            )

        audit_log(
            self.session,
            action='cessao.create',
            user_id=ctx.user.id,
            target_type='cessao',
            target_id=cessao.id,
            payload={
                'responsavel': data.responsavel,
                'centro_custo_destino': data.centro_custo_destino,
                'eletronico_ids': data.eletronico_ids,
            },
        )

        await self.session.commit()
        await self.session.refresh(cessao)
        itens = await self._itens_da_cessao(cessao.id)
        perifs = await self._perifericos_da_cessao(cessao.id)
        return self._serialize(cessao, itens, perifs)

    async def list_all(self, ctx: UserContext) -> list[dict]:
        is_full = ctx.is_privileged or ctx.is_tecnico_ti
        gestor_ccs = {
            cc for cc, ocup in ctx.ocupacoes.items() if ocup == 'Gestor'
        }

        if is_full:
            result = await self.session.execute(
                select(Cessao).order_by(Cessao.cedido_em.desc())
            )
        else:
            conditions = [Cessao.cedido_por_id == ctx.user.id]
            if gestor_ccs:
                cessao_ids_subq = (
                    select(CessaoEletronico.cessao_id)
                    .join(
                        Eletronico,
                        Eletronico.id == CessaoEletronico.eletronico_id,
                    )
                    .where(Eletronico.centro_custo.in_(gestor_ccs))
                )
                conditions.append(Cessao.id.in_(cessao_ids_subq))
            result = await self.session.execute(
                select(Cessao)
                .where(or_(*conditions))
                .order_by(Cessao.cedido_em.desc())
            )

        cessoes = list(result.scalars().all())
        if not cessoes:
            return []

        # Carrega todos os itens de todas as cessões em UMA query
        # (era N+1 antes — uma query por cessão).
        cessao_ids = [c.id for c in cessoes]
        itens_query = await self.session.execute(
            select(CessaoEletronico, Eletronico)
            .join(Eletronico, Eletronico.id == CessaoEletronico.eletronico_id)
            .where(CessaoEletronico.cessao_id.in_(cessao_ids))
        )
        itens_por_cessao: dict[int, list] = {cid: [] for cid in cessao_ids}
        for ce, el in itens_query.all():
            itens_por_cessao[ce.cessao_id].append((ce, el))

        # Periféricos de todas as cessões numa query só
        perifs_query = await self.session.execute(
            select(CessaoPeriferico)
            .where(CessaoPeriferico.cessao_id.in_(cessao_ids))
            .order_by(CessaoPeriferico.id)
        )
        perifs_por_cessao: dict[int, list] = {cid: [] for cid in cessao_ids}
        for p in perifs_query.scalars().all():
            perifs_por_cessao[p.cessao_id].append(p)

        return [
            self._serialize(
                c, itens_por_cessao[c.id], perifs_por_cessao[c.id]
            )
            for c in cessoes
        ]

    async def get_by_id(self, cessao_id: int, ctx: UserContext) -> dict:
        result = await self.session.execute(
            select(Cessao).where(Cessao.id == cessao_id)
        )
        cessao = result.scalar_one_or_none()
        if cessao is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Cessão não encontrada.',
            )

        itens = await self._itens_da_cessao(cessao_id)

        if not (ctx.is_privileged or ctx.is_tecnico_ti):
            gestor_ccs = {
                cc for cc, ocup in ctx.ocupacoes.items() if ocup == 'Gestor'
            }
            envolve_meu_cc = any(
                el.centro_custo in gestor_ccs for _, el in itens
            )
            if not envolve_meu_cc and cessao.cedido_por_id != ctx.user.id:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão para ver esta cessão.',
                )

        perifs = await self._perifericos_da_cessao(cessao_id)
        return self._serialize(cessao, itens, perifs)

    async def devolver(  # noqa: PLR0914
        self,
        cessao_id: int,
        ctx: UserContext,
        data: CessaoDevolverRequest,
    ) -> dict:
        """
        Qualquer usuário com **qualquer ocupação** em algum dos CCs de
        origem dos eletrônicos da cessão pode registrar a devolução.
        Admin/Tecnico_TI sempre podem.
        """
        is_full = ctx.is_privileged or ctx.is_tecnico_ti

        result = await self.session.execute(
            select(Cessao).where(Cessao.id == cessao_id)
        )
        cessao = result.scalar_one_or_none()
        if cessao is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Cessão não encontrada.',
            )

        if cessao.devolvida_em is not None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Cessão já devolvida.',
            )

        itens = await self._itens_da_cessao(cessao_id)

        if not is_full:
            ccs_origem = {el.centro_custo for _, el in itens}
            ccs_do_usuario = set(ctx.ocupacoes.keys())
            if not (ccs_origem & ccs_do_usuario):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail=(
                        'Apenas membros do CC de origem podem registrar '
                        'a devolução.'
                    ),
                )

        por_id = {el.id: (ce, el) for ce, el in itens}
        ids_pedidos = set(data.eletronico_ids)

        nao_pertencem = ids_pedidos - set(por_id.keys())
        if nao_pertencem:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=(
                    f'Eletrônicos não pertencem à cessão: '
                    f'{sorted(nao_pertencem)}'
                ),
            )

        ja_devolvidos = [
            i for i in ids_pedidos if por_id[i][0].devolvido_em is not None
        ]
        if ja_devolvidos:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=(
                    f'Eletrônicos já devolvidos: {sorted(ja_devolvidos)}'
                ),
            )

        lotes_existentes = [
            ce.devolucao_lote
            for ce, _ in itens
            if ce.devolucao_lote is not None
        ]
        proximo_lote = (max(lotes_existentes) + 1) if lotes_existentes else 1

        quando = (
            data.devolvida_em
            or datetime.now(tz=ZoneInfo('America/Sao_Paulo'))
        )

        data_retirada = cessao.cedido_em.date()
        if quando.date() < data_retirada:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=(
                    'A data de devolução não pode ser anterior à data '
                    f'de retirada ({data_retirada.strftime("%d/%m/%Y")}).'
                ),
            )

        for i in ids_pedidos:
            ce, el = por_id[i]
            ce.devolvido_em = quando
            ce.devolvida_por_id = ctx.user.id
            ce.devolucao_lote = proximo_lote
            el.status = 'Interno'
            el.localizacao = None

        pendentes_apos = sum(
            1
            for ce, _ in itens
            if ce.devolvido_em is None
            and ce.eletronico_id not in ids_pedidos
        )
        if pendentes_apos == 0:
            cessao.devolvida_em = quando
            cessao.devolvida_por_id = ctx.user.id

        audit_log(
            self.session,
            action='cessao.devolver',
            user_id=ctx.user.id,
            target_type='cessao',
            target_id=cessao_id,
            payload={
                'eletronico_ids': sorted(ids_pedidos),
                'lote': proximo_lote,
                'parcial': pendentes_apos > 0,
            },
        )

        await self.session.commit()
        await self.session.refresh(cessao)
        itens_atualizados = await self._itens_da_cessao(cessao_id)
        perifs = await self._perifericos_da_cessao(cessao_id)
        return self._serialize(cessao, itens_atualizados, perifs)

    async def recebimentos_pendentes_gestor(
        self, ctx: UserContext
    ) -> dict:
        """
        Retorna devoluções (lotes) ainda não confirmadas.
        - Admin / Tecnico_TI: **todas** sem restrição de CC.
        - Gestor: apenas em CCs onde ele tem ocupação Gestor.
        - Demais: lista vazia.

        Obs.: o estado `gestor_visto_em` é compartilhado entre os papéis
        de supervisão — quando qualquer Admin/TI/Gestor abre /cessoes
        (chamando o `marcar_recebimentos_vistos`), a notificação some
        para todos.
        """
        is_full = ctx.is_privileged or ctx.is_tecnico_ti
        query = (
            select(
                CessaoEletronico.cessao_id,
                CessaoEletronico.devolucao_lote,
                CessaoEletronico.devolvido_em,
                CessaoEletronico.devolvida_por_id,
            )
            .join(
                Eletronico,
                Eletronico.id == CessaoEletronico.eletronico_id,
            )
            .where(
                CessaoEletronico.devolvido_em.is_not(None),
                CessaoEletronico.gestor_visto_em.is_(None),
            )
        )

        if not is_full:
            gestor_ccs = [
                cc
                for cc, ocup in ctx.ocupacoes.items()
                if ocup == 'Gestor'
            ]
            if not gestor_ccs:
                return {'count': 0, 'items': []}
            query = query.where(Eletronico.centro_custo.in_(gestor_ccs))

        result = await self.session.execute(query)
        rows = result.all()
        unique: dict[tuple[int, int], dict] = {}
        for cessao_id, lote, devolvido_em, devolvida_por_id in rows:
            key = (cessao_id, lote or 1)
            if key not in unique:
                unique[key] = {
                    'cessao_id': cessao_id,
                    'lote': lote or 1,
                    'devolvida_em': devolvido_em,
                    'devolvida_por_id': devolvida_por_id,
                }
        items = sorted(
            unique.values(),
            key=lambda x: x['devolvida_em'],
            reverse=True,
        )
        return {'count': len(items), 'items': items}

    async def marcar_recebimentos_vistos(
        self, ctx: UserContext
    ) -> dict:
        """
        Marca devoluções pendentes (gestor_visto_em IS NULL) como vistas.
        - Admin / Tecnico_TI: marca **todas**, sem restrição de CC.
        - Gestor: apenas das devoluções em CCs onde é Gestor.
        - Demais: no-op.
        """
        is_full = ctx.is_privileged or ctx.is_tecnico_ti
        agora = datetime.now(tz=ZoneInfo('America/Sao_Paulo'))

        query = select(CessaoEletronico).where(
            CessaoEletronico.devolvido_em.is_not(None),
            CessaoEletronico.gestor_visto_em.is_(None),
        )

        if not is_full:
            gestor_ccs = [
                cc
                for cc, ocup in ctx.ocupacoes.items()
                if ocup == 'Gestor'
            ]
            if not gestor_ccs:
                return {'marcadas': 0}
            sub = (
                select(CessaoEletronico.eletronico_id)
                .join(
                    Eletronico,
                    Eletronico.id == CessaoEletronico.eletronico_id,
                )
                .where(Eletronico.centro_custo.in_(gestor_ccs))
            )
            query = query.where(CessaoEletronico.eletronico_id.in_(sub))

        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        for ce in rows:
            ce.gestor_visto_em = agora
        await self.session.commit()
        return {'marcadas': len(rows)}

    async def delete(self, cessao_id: int, ctx: UserContext) -> dict:
        """
        Admin: sem restrição.
        Gestor: pode apagar cessões em que ao menos um eletrônico
        pertença a um CC onde ele tem ocupação `Gestor`.
        Demais perfis: 403.

        Ao apagar uma cessão em aberto, retorna os eletrônicos ainda
        externos a `Interno` e zera a localização.
        """
        result = await self.session.execute(
            select(Cessao).where(Cessao.id == cessao_id)
        )
        cessao = result.scalar_one_or_none()
        if cessao is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Cessão não encontrada.',
            )

        itens = await self._itens_da_cessao(cessao_id)

        if not ctx.is_privileged:
            gestor_ccs = {
                cc
                for cc, ocup in ctx.ocupacoes.items()
                if ocup == 'Gestor'
            }
            ccs_origem = {el.centro_custo for _, el in itens}
            if not (ccs_origem & gestor_ccs):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail=(
                        'Apenas Admin ou Gestor de algum CC envolvido '
                        'pode excluir esta cessão.'
                    ),
                )

        # Itens ainda fora voltam pro estoque
        for ce, el in itens:
            if ce.devolvido_em is None and el.status == 'Externo':
                el.status = 'Interno'
                el.localizacao = None

        perifs = await self._perifericos_da_cessao(cessao_id)
        snapshot = self._serialize(cessao, itens, perifs)
        audit_log(
            self.session,
            action='cessao.delete',
            user_id=ctx.user.id,
            target_type='cessao',
            target_id=cessao.id,
            payload={
                'responsavel': cessao.responsavel,
                'centro_custo_destino': cessao.centro_custo_destino,
                'status_antes': snapshot['status'],
                'eletronico_ids': [
                    el.id for _, el in itens
                ],
            },
        )
        await self.session.delete(cessao)
        await self.session.commit()
        return snapshot
