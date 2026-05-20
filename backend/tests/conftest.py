import asyncio
from http import HTTPStatus
from random import choice

import pytest_asyncio
from factory.base import Factory
from factory.declarations import LazyAttribute, Sequence
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.core.database import Base
from backend.core.engine import EngineApp
from backend.core.limiter import limiter
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.tipo_eletronico import TipoEletronico
from backend.model.user import User
from backend.security.security import Security

# Desabilita rate-limit em testes (cada teste faz vários logins).
limiter.enabled = False

DATABASE_URL = 'sqlite+aiosqlite:///'
BASE_URL = 'http://127.0.0.1:8000'


@pytest_asyncio.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='session')
async def async_engine():
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_db(async_engine):
    async with async_engine.connect() as conn:
        trans = await conn.begin()

        session = AsyncSession(bind=conn, expire_on_commit=False)

        nested = await conn.begin_nested()  # SAVEPOINT

        # Seed do catálogo de tipos — mesmos da migration de produção
        for nome in [
            'Computador', 'Notbook', 'Monitor', 'Impressora', 'Scanner',
        ]:
            session.add(TipoEletronico(nome=nome, ativo=True))
        await session.flush()

        try:
            yield session
        finally:
            await session.close()
            await nested.rollback()
            await trans.rollback()


@pytest_asyncio.fixture
async def async_client(async_db):
    async def override_get_db():
        try:
            yield async_db
        finally:
            await async_db.flush()

    app.dependency_overrides[EngineApp.get_async_session] = override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport, base_url=BASE_URL
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


class FactoryUser(Factory):
    class Meta:
        model = User

    nome = Sequence(lambda n: f'Teste{n}')
    email = LazyAttribute(lambda obj: f'{obj.nome}@teste.com')
    senha = LazyAttribute(lambda obj: f'{obj.nome}123')
    tipo = 'Admin'


@pytest_asyncio.fixture
async def usuario_teste():
    data = FactoryUser().__dict__
    data.pop('_sa_instance_state', None)
    return data


_TIPOS_ELETRONICO_VALIDOS = [
    'Computador',
    'Notbook',
    'Monitor',
    'Impressora',
    'Scanner',
]
_STATUSES_ELETRONICO_VALIDOS = ['Interno', 'Externo', 'Em Manutenção']


class FactoryEletronico(Factory):
    class Meta:
        model = Eletronico

    numero_serie = Sequence(lambda n: f'SN{n}')
    numero_patrimonio = Sequence(lambda n: f'00{n}')
    nome = Sequence(lambda n: f'UFC{n}')
    marca = 'DELL'
    # LazyAttribute para reavaliar a cada instância (choice no nível
    # da classe é avaliado uma única vez, criando flakiness)
    tipo = LazyAttribute(lambda _: choice(_TIPOS_ELETRONICO_VALIDOS))
    modelo = 'XPS 15'
    status = LazyAttribute(lambda _: choice(_STATUSES_ELETRONICO_VALIDOS))
    ip = Sequence(lambda n: f'10.0.0.{n}')
    localizacao = 'Sala de TI'
    descricao = LazyAttribute(lambda obj: f'Descrição de {obj.nome}')
    centro_custo = Sequence(lambda n: f'000{n}')


@pytest_asyncio.fixture
async def eletronico_teste():
    data = FactoryEletronico().__dict__
    data.pop('_sa_instance_state', None)
    return data


class FactoryContrato(Factory):
    class Meta:
        model = Contrato

    centro_custo = Sequence(lambda n: f'000{n}')
    descricao = LazyAttribute(lambda obj: f'Descrição de {obj.centro_custo}')


@pytest_asyncio.fixture
async def contrato_teste():
    data = FactoryContrato().__dict__
    data.pop('_sa_instance_state', None)
    return data


@pytest_asyncio.fixture
async def login_teste(async_client, async_db, usuario_teste):
    """
    Cria o usuário Admin diretamente no banco (bypassando a restrição do
    endpoint público que força tipo=Funcionario) e retorna o token de acesso.
    """
    user = usuario_teste
    security = Security()

    # Inserir Admin diretamente no banco
    user_db = User(
        nome=user['nome'],
        email=user['email'],
        senha=security.get_senha_hash(user['senha']),
        tipo=user['tipo'],  # 'Admin'
    )
    async_db.add(user_db)
    await async_db.commit()
    await async_db.refresh(user_db)

    # Fazer login via API para obter token
    form_data = {
        'username': user['email'],
        'password': user['senha'],
    }
    response = await async_client.post('/auth/login', data=form_data)
    assert response.status_code == HTTPStatus.OK

    return {'token': response.json()['access_token'], 'user': user}
