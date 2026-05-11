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
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User

DATABASE_URL = 'sqlite+aiosqlite://'
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
    #     'Admin',
    #     'Funcionario',
    #     'Gestor',
    #     'Subgestor',
    #     'Tecnico_TI',
    # ])


@pytest_asyncio.fixture
async def usuario_teste():
    data = FactoryUser().__dict__
    data.pop('_sa_instance_state', None)
    return data


class FactoryEletronico(Factory):
    class Meta:
        model = Eletronico

    numero_serie = Sequence(lambda n: f'SN{n}')
    numero_patrimonio = Sequence(lambda n: f'00{n}')
    nome = Sequence(lambda n: f'UFC{n}')
    marca = 'DELL'
    tipo = choice([
        'Notebook',
        'Pc',
        'Impressora',
        'Scanner',
        'monitor',
    ])
    modelo = 'XPS 15'
    status = choice([
        'Interno',
        'Externo',
        'Em Manutenção',
    ])
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
async def login_teste(async_client, usuario_teste):
    user = usuario_teste

    await async_client.post('/users/', json=user)

    form_data = {
        'username': user['email'],
        'password': user['senha'],
    }
    response = await async_client.post('/auth/login', data=form_data)
    assert response.status_code == HTTPStatus.OK

    return {'token': response.json()['access_token'], 'user': user}
