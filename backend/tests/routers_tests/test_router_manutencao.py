"""Tela de Administração: backup, limpeza e restauração.

Uma tela que apaga banco não pode depender de estar escondida no menu.
"""

from http import HTTPStatus

import pytest
from sqlalchemy import select

from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from tests.support import oidc


URL = '/manutencao'
SUB = 'dddddddd-0000-0000-0000-000000000001'
NO_CT1 = 2
NO_TOTAL = 3


async def _entrar(async_db, tipo: str, email: str) -> dict[str, str]:
    async_db.add(
        User(
            nome=f'{tipo} {email}',
            email=email,
            tipo=tipo,
            external_id=SUB + email,
        )
    )
    await async_db.commit()
    return {'Authorization': f'Bearer {oidc.cunhar_token(SUB + email, email)}'}


ROTAS = [
    ('get', f'{URL}/backups', None),
    ('post', f'{URL}/backups', {}),
    ('get', f'{URL}/alvos', None),
    ('post', f'{URL}/limpeza', {'alvo': 'tudo', 'confirmacao': 'LIMPAR'}),
    ('post', f'{URL}/contagem', {'alvo': 'tudo'}),
    (
        'post',
        f'{URL}/restauracao',
        {'nome': 'x.dump', 'confirmacao': 'RESTAURAR'},
    ),
]


@pytest.mark.asyncio
@pytest.mark.routers
@pytest.mark.parametrize(
    'tipo', ['Funcionario', 'Gestor', 'Subgestor', 'Tecnico_TI']
)
async def test_so_admin_entra(async_client, async_db, tipo):
    """Tecnico_TI também não entra.

    Ele tem passe livre em eletrônicos, que é o domínio dele; restaurar ou
    limpar o banco é outra categoria de poder.
    """
    headers = await _entrar(async_db, tipo, f'{tipo.lower()}@ufc.com.br')

    for metodo, caminho, corpo in ROTAS:
        chamada = getattr(async_client, metodo)
        resposta = (
            await chamada(caminho, headers=headers)
            if corpo is None
            else await chamada(caminho, json=corpo, headers=headers)
        )
        assert resposta.status_code == HTTPStatus.FORBIDDEN, (
            f'{tipo} passou em {metodo.upper()} {caminho}'
        )


@pytest.mark.asyncio
@pytest.mark.routers
async def test_sem_token_nao_entra(async_client):
    resposta = await async_client.get(f'{URL}/backups')
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_admin_ve_os_alvos(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'chefe@ufc.com.br')
    resposta = await async_client.get(f'{URL}/alvos', headers=headers)

    assert resposta.status_code == HTTPStatus.OK
    chaves = {a['chave'] for a in resposta.json()}
    assert chaves == {
        'eletronicos',
        'cessoes',
        'solicitacoes',
        'catalogo',
        'auditoria',
        'tudo',
    }
    # Centros de custo NÃO são alvo: vêm sincronizados da receita, e limpar aqui
    # seria desfeito no ciclo seguinte.
    assert 'contratos' not in chaves
    assert 'usuarios' not in chaves


@pytest.mark.asyncio
@pytest.mark.routers
async def test_limpeza_sem_a_palavra_certa_nao_apaga(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'chefe@ufc.com.br')
    resposta = await async_client.post(
        f'{URL}/limpeza',
        json={'alvo': 'tudo', 'confirmacao': 'limpar'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST
    assert 'LIMPAR' in resposta.json()['detail']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_alvo_invalido_e_recusado(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'chefe@ufc.com.br')
    resposta = await async_client.post(
        f'{URL}/limpeza',
        json={'alvo': 'tb_users', 'confirmacao': 'LIMPAR'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_filtro_por_cc_recusado_em_alvo_que_nao_aceita(
    async_client, async_db
):
    """`auditoria` não se liga a centro de custo; aceitar o filtro em silêncio
    apagaria a auditoria inteira achando que era só a de um CC."""
    headers = await _entrar(async_db, 'Admin', 'chefe@ufc.com.br')
    resposta = await async_client.post(
        f'{URL}/limpeza',
        json={
            'alvo': 'auditoria',
            'centro_custo': '4453',
            'confirmacao': 'LIMPAR',
        },
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_download_recusa_travessia_de_caminho(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'chefe@ufc.com.br')
    for nome in ['../../etc/passwd', 'qualquer.txt']:
        resposta = await async_client.get(
            f'{URL}/backups/{nome}', headers=headers
        )
        assert resposta.status_code in (
            HTTPStatus.NOT_FOUND,
            HTTPStatus.BAD_REQUEST,
        ), f'{nome} não foi barrado'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_contagem_diz_quanto_sai_sem_apagar(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'conta@ufc.com.br')
    async_db.add_all([
        Contrato(centro_custo='CT1', descricao='a'),
        Contrato(centro_custo='CT2', descricao='b'),
    ])
    for i, cc in enumerate(['CT1', 'CT1', 'CT2']):
        async_db.add(
            Eletronico(
                numero_serie=f'SN-CT{i}',
                numero_patrimonio=f'PAT-CT{i}',
                nome=f'EQ-CT{i}',
                tipo='Monitor',
                status='Interno',
                centro_custo=cc,
            )
        )
    await async_db.commit()

    resposta = await async_client.post(
        f'{URL}/contagem',
        json={'alvo': 'eletronicos', 'centro_custo': 'CT1'},
        headers=headers,
    )

    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json()['detalhes']['tb_eletronicos'] == NO_CT1
    restantes = (await async_db.execute(select(Eletronico))).scalars().all()
    assert len(restantes) == NO_TOTAL


@pytest.mark.asyncio
@pytest.mark.routers
async def test_contagem_de_alvo_invalido_e_recusada(async_client, async_db):
    headers = await _entrar(async_db, 'Admin', 'conta2@ufc.com.br')
    resposta = await async_client.post(
        f'{URL}/contagem', json={'alvo': 'usuarios'}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST
