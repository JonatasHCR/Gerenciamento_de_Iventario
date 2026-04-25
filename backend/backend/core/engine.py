from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from backend.core.settings import Settings


class EngineApp:
    def __init__(self):
        self.DATABASE_URL_ASYNC = Settings().database_url_async()
        self.DATABASE_URL_SYNC = Settings().database_url_sync()

        self.async_engine = create_async_engine(
            self.DATABASE_URL_ASYNC,
            echo=True,
        )

        self.sync_engine = create_engine(
            self.DATABASE_URL_SYNC,
            echo=True,
        )

    async def get_async_session(self):

        SessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()

    def get_sync_session(self):

        SessionLocal = sessionmaker(
            bind=self.sync_engine,
            class_=Session,
            expire_on_commit=False,
        )

        with SessionLocal() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
