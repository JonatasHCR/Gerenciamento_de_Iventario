from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.settings import Settings


class EngineApp:  # pragma: no cover
    def __init__(self):
        self.DATABASE_URL_ASYNC = Settings().database_url_async()

        self.async_engine = create_async_engine(
            self.DATABASE_URL_ASYNC,
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
