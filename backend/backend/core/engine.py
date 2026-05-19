from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.settings import Settings

_settings = Settings()


class EngineApp:  # pragma: no cover
    DATABASE_URL_ASYNC = _settings.database_url_async()

    engine = create_async_engine(
        DATABASE_URL_ASYNC,
        echo=_settings.DEBUG,
    )

    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    @staticmethod
    async def get_async_session():

        async with EngineApp.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()
