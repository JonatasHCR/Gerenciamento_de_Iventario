"""Sincronização de centros de custo a partir da receita.

Cada teste cobre uma das regras que sustentam o desenho — e que, se caírem,
falham em silêncio: dado apagado, vínculo local sobrescrito, CC fantasma.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.user import User
from backend.service.sync_receita import SyncReceita


class _SettingsFake:
    RECEITA_API_URL = 'http://receita-de-teste:3040'
    RECEITA_API_TOKEN = 'token-de-teste'


def _sync(session, cost_centers, deletions=None):
    """SyncReceita com o HTTP trocado por respostas fixas."""
    servico = SyncReceita(session, _SettingsFake())

    async def buscar(caminho, params):
        if caminho.endswith('/deletions'):
            return {'deletions': deletions or []}
        return {'cost_centers': cost_centers}

    servico._buscar = buscar
    return servico


def _cc(cr_code, descricao='Obra', coordenadores=None, cliente='ACME'):
    return {
        'cr_code': cr_code,
        'description': descricao,
        'coordinator': ' / '.join(coordenadores or []),
        'coordinator_list': coordenadores or [],
        'client': {'name': cliente, 'full_name': f'{cliente} Ltda'},
    }


@pytest.mark.asyncio
@pytest.mark.service
async def test_primeira_carga_cria_os_contratos(async_db):
    resultado = await _sync(
        async_db, [_cc('4453', 'Obra da Ponte'), _cc('4501', 'Reforma')]
    ).executar()

    assert resultado.criados == 2
    contratos = (await async_db.execute(select(Contrato))).scalars().all()
    assert {c.centro_custo for c in contratos} == {'4453', '4501'}

    ponte = await async_db.get(Contrato, '4453')
    assert ponte.descricao == 'Obra da Ponte'
    assert ponte.cliente_nome == 'ACME'
    assert ponte.cliente_full_name == 'ACME Ltda'
    assert ponte.ativo is True
    assert ponte.sincronizado_em is not None


@pytest.mark.asyncio
@pytest.mark.service
async def test_segunda_rodada_atualiza_sem_duplicar(async_db):
    await _sync(async_db, [_cc('4453', 'Nome Antigo')]).executar()
    resultado = await _sync(async_db, [_cc('4453', 'Nome Novo')]).executar()

    assert resultado.criados == 0
    assert resultado.atualizados == 1
    contratos = (await async_db.execute(select(Contrato))).scalars().all()
    assert len(contratos) == 1
    assert contratos[0].descricao == 'Nome Novo'


@pytest.mark.asyncio
@pytest.mark.service
async def test_cc_aceita_codigo_com_mais_de_quatro_caracteres(async_db):
    """O motivo do alargamento String(4) -> String(20).

    Hoje todos os cr_code reais têm 4 caracteres, mas `cost_centers.cr_code` na
    receita é string sem limite — os specs de lá usam 'CASC-1', 'MVREQ-1'.
    """
    await _sync(async_db, [_cc('MVREQ-1', 'Contrato longo')]).executar()

    contrato = await async_db.get(Contrato, 'MVREQ-1')
    assert contrato is not None
    assert contrato.descricao == 'Contrato longo'


@pytest.mark.asyncio
@pytest.mark.service
async def test_cc_apagado_na_receita_vira_inativo_e_nao_e_deletado(async_db):
    """Nunca DELETE.

    Há FKs de tb_eletronicos, tb_cessoes e tb_solicitacoes apontando para
    tb_contratos: apagar violaria integridade e levaria histórico junto.
    """
    await _sync(async_db, [_cc('4453')]).executar()

    await _sync(
        async_db, [], deletions=[{'cr_code': '4453', 'deleted_at': 'x'}]
    ).executar()

    contrato = await async_db.get(Contrato, '4453')
    assert contrato is not None, 'o contrato não pode ser removido'
    assert contrato.ativo is False


@pytest.mark.asyncio
@pytest.mark.service
async def test_gestor_com_conta_local_vira_vinculo_de_origem_receita(async_db):
    async_db.add(User(nome='Ana Pereira', email='ana@ufc.com.br', tipo='Funcionario'))
    await async_db.commit()

    resultado = await _sync(
        async_db, [_cc('4453', coordenadores=['Ana Pereira'])]
    ).executar()

    assert resultado.gestores_vinculados == 1
    assoc = (
        await async_db.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.centro_custo == '4453'
            )
        )
    ).scalar_one()
    assert assoc.ocupacao == 'Gestor'
    assert assoc.origem == 'receita'


@pytest.mark.asyncio
@pytest.mark.service
async def test_coordenador_sem_conta_fica_so_no_texto(async_db):
    """A receita admite coordenador externo.

    Sem `gestor_nomes` guardando o texto completo, esses nomes sumiriam da tela
    — só existiria o vínculo, e ele não pode ser criado sem usuário local.
    """
    resultado = await _sync(
        async_db, [_cc('4453', coordenadores=['Fulano Externo'])]
    ).executar()

    assert resultado.gestores_vinculados == 0
    assert 'Fulano Externo' in resultado.gestores_sem_conta

    contrato = await async_db.get(Contrato, '4453')
    assert contrato.gestor_nomes == 'Fulano Externo'


@pytest.mark.asyncio
@pytest.mark.service
async def test_sync_nao_toca_em_vinculos_locais(async_db):
    """A razão de existir da coluna `origem`.

    Funcionario e Subgestor continuam sendo cadastro local. Se o sync
    gerenciasse todas as linhas, apagaria esses vínculos a cada rodada.
    """
    async_db.add(Contrato(centro_custo='4453', descricao='Obra'))
    async_db.add(User(nome='Beto Local', email='beto@ufc.com.br', tipo='Funcionario'))
    await async_db.flush()
    beto = (
        await async_db.execute(select(User).where(User.nome == 'Beto Local'))
    ).scalar_one()
    async_db.add(
        AssociacaoUserContrato(
            centro_custo='4453', user_id=beto.id,
            ocupacao='Funcionario', origem='local',
        )
    )
    await async_db.commit()

    await _sync(async_db, [_cc('4453', coordenadores=[])]).executar()

    assoc = (
        await async_db.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.user_id == beto.id
            )
        )
    ).scalar_one_or_none()
    assert assoc is not None, 'vínculo local não pode ser apagado pelo sync'
    assert assoc.ocupacao == 'Funcionario'


@pytest.mark.asyncio
@pytest.mark.service
async def test_gestor_removido_na_receita_perde_o_vinculo(async_db):
    async_db.add(User(nome='Ana Pereira', email='ana@ufc.com.br', tipo='Funcionario'))
    await async_db.commit()

    await _sync(async_db, [_cc('4453', coordenadores=['Ana Pereira'])]).executar()
    await _sync(async_db, [_cc('4453', coordenadores=[])]).executar()

    restantes = (
        await async_db.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.centro_custo == '4453'
            )
        )
    ).scalars().all()
    assert restantes == []


@pytest.mark.asyncio
@pytest.mark.service
async def test_nao_promove_a_gestor_quem_ja_tem_vinculo_local(async_db):
    """Promover apagaria um cadastro que o sync não gerencia."""
    async_db.add(Contrato(centro_custo='4453', descricao='Obra'))
    async_db.add(User(nome='Ana Pereira', email='ana@ufc.com.br', tipo='Funcionario'))
    await async_db.flush()
    ana = (
        await async_db.execute(select(User).where(User.nome == 'Ana Pereira'))
    ).scalar_one()
    async_db.add(
        AssociacaoUserContrato(
            centro_custo='4453', user_id=ana.id,
            ocupacao='Funcionario', origem='local',
        )
    )
    await async_db.commit()

    await _sync(async_db, [_cc('4453', coordenadores=['Ana Pereira'])]).executar()

    assoc = await async_db.get(AssociacaoUserContrato, ('4453', ana.id))
    assert assoc.ocupacao == 'Funcionario'
    assert assoc.origem == 'local'


@pytest.mark.asyncio
@pytest.mark.service
async def test_cc_sem_codigo_e_ignorado(async_db):
    resultado = await _sync(async_db, [_cc(''), _cc('4453')]).executar()
    assert resultado.criados == 1


@pytest.mark.asyncio
@pytest.mark.service
async def test_marca_dagua_e_o_maior_sincronizado_em(async_db):
    servico = _sync(async_db, [_cc('4453')])
    assert await servico._marca_dagua() is None

    await servico.executar()

    marca = await servico._marca_dagua()
    assert marca is not None

    convertida = datetime.fromisoformat(marca)
    # Com offset explícito, sempre: sem ele a receita interpretaria a marca no
    # fuso dela e a janela de sincronização escorregaria três horas.
    assert convertida.tzinfo is not None
    assert convertida <= datetime.now(timezone.utc)
