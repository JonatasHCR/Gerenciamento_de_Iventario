"""Sincroniza os centros de custo a partir da receita.

A receita é a dona deste dado. Até aqui o inventário mantinha à mão uma cópia
incompleta em `tb_contratos` — centro de custo, descrição, gestor e cliente
digitados de novo, e desatualizando em silêncio. Este serviço substitui aquele
cadastro.

Regras que sustentam o desenho:

- **Upsert por `cr_code`**, com marca d'água em `sincronizado_em`.
- **Nunca deletar.** CC removido na receita vira `ativo = False`. Há FKs de
  `tb_eletronicos`, `tb_cessoes` e `tb_solicitacoes` apontando para
  `tb_contratos`; um DELETE violaria integridade e apagaria histórico.
- **Gestores nos dois lugares.** `gestor_nomes` recebe o texto completo (para
  exibir sempre) e `tb_associacao_user_contrato` recebe `ocupacao='Gestor',
  origem='receita'` apenas quando existe usuário local com aquele nome — a
  receita admite coordenador que não tem conta aqui.
- **O sync só toca linhas `origem='receita'`.** Funcionario e Subgestor
  continuam sendo cadastro local e são intocados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.settings import Settings
from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.user import User

logger = logging.getLogger(__name__)

OCUPACAO_GESTOR = 'Gestor'
ORIGEM_RECEITA = 'receita'


@dataclass
class Resultado:
    criados: int = 0
    atualizados: int = 0
    desativados: int = 0
    gestores_vinculados: int = 0
    gestores_sem_conta: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        partes = [
            f'{self.criados} criados',
            f'{self.atualizados} atualizados',
            f'{self.desativados} desativados',
            f'{self.gestores_vinculados} gestores vinculados',
        ]
        if self.gestores_sem_conta:
            partes.append(
                f'{len(self.gestores_sem_conta)} coordenador(es) sem conta local'
            )
        return ', '.join(partes)


class SyncReceita:
    """Cliente da API de sincronização da receita."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None):
        self.session = session
        self.settings = settings or Settings()

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _buscar(self, caminho: str, params: dict) -> dict:
        url = f'{self.settings.RECEITA_API_URL.rstrip("/")}{caminho}'
        cabecalhos = {
            'Authorization': f'Bearer {self.settings.RECEITA_API_TOKEN}'
        }
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            resposta = await cliente.get(url, params=params, headers=cabecalhos)
            resposta.raise_for_status()
            return resposta.json()

    # ------------------------------------------------------------------
    # Marca d'água
    # ------------------------------------------------------------------

    async def _marca_dagua(self) -> str | None:
        """A sincronização mais recente. `None` na primeira carga."""
        resultado = await self.session.execute(
            select(Contrato.sincronizado_em)
            .where(Contrato.sincronizado_em.is_not(None))
            .order_by(Contrato.sincronizado_em.desc())
            .limit(1)
        )
        ultimo = resultado.scalar_one_or_none()
        if ultimo is None:
            return None

        # Sempre com offset explícito. Um timestamp sem fuso seria interpretado
        # pelo `Time.zone.parse` da receita no fuso DELA — America/Sao_Paulo,
        # três horas de diferença — e a marca d'água pularia (ou repetiria)
        # registros em silêncio. O Postgres devolve aware (a coluna é
        # timezone=True); o SQLite dos testes, não.
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=timezone.utc)
        return ultimo.astimezone(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    async def executar(self) -> Resultado:
        resultado = Resultado()
        agora = datetime.now(timezone.utc)
        desde = await self._marca_dagua()

        params = {'updated_since': desde} if desde else {}
        dados = await self._buscar('/api/v1/cost_centers', params)

        # Nomes de usuário → id, numa consulta só. A alternativa seria uma
        # consulta por coordenador de cada CC.
        usuarios = await self._mapa_de_usuarios()

        for cc in dados.get('cost_centers', []):
            await self._aplicar(cc, usuarios, agora, resultado)

        if desde:
            # Exclusões só fazem sentido a partir da segunda rodada: na primeira
            # carga não há nada local para desativar.
            await self._aplicar_exclusoes(desde, agora, resultado)

        await self.session.commit()
        logger.info('sync receita: %s', resultado.resumo())
        if resultado.gestores_sem_conta:
            # Não é erro: a receita admite coordenador externo. Mas vale
            # aparecer no log, porque é o caso em que o vínculo por usuário não
            # acontece e só o texto em `gestor_nomes` fica.
            logger.info(
                'coordenadores sem conta no inventario (so em gestor_nomes): %s',
                ', '.join(sorted(set(resultado.gestores_sem_conta))),
            )
        return resultado

    async def _mapa_de_usuarios(self) -> dict[str, int]:
        resultado = await self.session.execute(select(User.id, User.nome))
        return {nome.strip().lower(): id_ for id_, nome in resultado.all()}

    async def _aplicar(
        self,
        cc: dict,
        usuarios: dict[str, int],
        agora: datetime,
        resultado: Resultado,
    ) -> None:
        codigo = (cc.get('cr_code') or '').strip()
        if not codigo:
            return

        cliente = cc.get('client') or {}
        campos = {
            'descricao': (cc.get('description') or '').strip() or codigo,
            'cliente_nome': cliente.get('name'),
            'cliente_full_name': cliente.get('full_name'),
            'gestor_nomes': cc.get('coordinator'),
            'ativo': True,
            'sincronizado_em': agora,
        }

        existente = await self.session.get(Contrato, codigo)
        if existente is None:
            self.session.add(Contrato(centro_custo=codigo, **campos))
            resultado.criados += 1
        else:
            for chave, valor in campos.items():
                setattr(existente, chave, valor)
            resultado.atualizados += 1

        # `flush` antes de mexer nas associações: a FK exige que o contrato já
        # exista quando o vínculo do gestor for inserido.
        await self.session.flush()
        await self._sincronizar_gestores(
            codigo, cc.get('coordinator_list') or [], usuarios, resultado
        )

    async def _sincronizar_gestores(
        self,
        centro_custo: str,
        coordenadores: list[str],
        usuarios: dict[str, int],
        resultado: Resultado,
    ) -> None:
        desejados: set[int] = set()
        for nome in coordenadores:
            id_usuario = usuarios.get(nome.strip().lower())
            if id_usuario is None:
                resultado.gestores_sem_conta.append(nome)
                continue
            desejados.add(id_usuario)

        atuais = await self.session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.centro_custo == centro_custo,
                AssociacaoUserContrato.origem == ORIGEM_RECEITA,
            )
        )
        atuais = {a.user_id: a for a in atuais.scalars().all()}

        # Quem saiu da lista de coordenadores na receita. Só linhas
        # `origem='receita'` chegam aqui — vínculos locais são intocados.
        for id_usuario, associacao in atuais.items():
            if id_usuario not in desejados:
                await self.session.delete(associacao)

        for id_usuario in desejados - atuais.keys():
            ja_local = await self.session.get(
                AssociacaoUserContrato, (centro_custo, id_usuario)
            )
            if ja_local is not None:
                # A pessoa já tem vínculo local neste CC (como Funcionario, por
                # exemplo). Promover para Gestor aqui apagaria um cadastro que o
                # sync não gerencia, então deixamos como está.
                continue
            self.session.add(
                AssociacaoUserContrato(
                    centro_custo=centro_custo,
                    user_id=id_usuario,
                    ocupacao=OCUPACAO_GESTOR,
                    origem=ORIGEM_RECEITA,
                )
            )
            resultado.gestores_vinculados += 1

        await self.session.flush()

    async def _aplicar_exclusoes(
        self, desde: str, agora: datetime, resultado: Resultado
    ) -> None:
        dados = await self._buscar(
            '/api/v1/cost_centers/deletions', {'since': desde}
        )
        codigos = [
            (d.get('cr_code') or '').strip()
            for d in dados.get('deletions', [])
            if d.get('cr_code')
        ]
        if not codigos:
            return

        # `ativo = False`, nunca DELETE: eletrônicos, cessões e solicitações
        # apontam para estas linhas. O CC some do cadastro novo e continua
        # legível no histórico.
        efeito = await self.session.execute(
            update(Contrato)
            .where(Contrato.centro_custo.in_(codigos), Contrato.ativo.is_(True))
            .values(ativo=False, sincronizado_em=agora)
        )
        resultado.desativados += efeito.rowcount or 0
