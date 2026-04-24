import asyncio

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.core.engine import Base, get_db

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

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport, base_url=BASE_URL
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def usuario_teste():
    return {
        'nome': 'João Silva',
        'email': 'joao.silva@example.com',
        'senha': 'senha123',
        'tipo': 'funcionario',
    }


@pytest_asyncio.fixture
async def eletronico_teste():
    return {
        'numero_serie': 'SN123456789',
        'numero_patrimonio': 'PT123456789',
        'nome': 'Notebook Dell',
        'marca': 'Dell',
        'tipo': 'Notebook',
        'modelo': 'XPS 15',
        'status': 'Interno',
        'ip': '10.0.0.0',
        'centro_custo': '0001',
    }


@pytest_asyncio.fixture
async def contrato_teste():
    return {
        'centro_custo': '5582',
        'descricao': 'Contrato de manutenção de computadores',
    }
