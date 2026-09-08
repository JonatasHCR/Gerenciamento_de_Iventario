"""Ponto de entrada da sincronização de centros de custo com a receita.

Roda a cada 15 minutos pelo container `sync` do docker-compose, no mesmo estilo
do `db-backup` que já existia. Um scheduler dentro do processo do FastAPI seria
mais simples de escrever, mas multiplicaria com réplicas — duas instâncias
sincronizando o mesmo dado ao mesmo tempo.

Uso manual (útil para a primeira carga e para depurar):
    python sync_receita.py
"""

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.settings import Settings
from backend.service.sync_receita import SyncReceita

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger('sync_receita')


async def main() -> int:
    settings = Settings()

    if not settings.RECEITA_API_URL or not settings.RECEITA_API_TOKEN:
        logger.error(
            'RECEITA_API_URL e RECEITA_API_TOKEN precisam estar definidos. '
            'O token e o mesmo SYNC_API_TOKEN do .env da receita.'
        )
        return 2

    engine = create_async_engine(settings.database_url_async())
    Sessao = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with Sessao() as sessao:
            resultado = await SyncReceita(sessao, settings).executar()
        logger.info('concluido: %s', resultado.resumo())
        return 0
    except Exception:
        # Falhar barulhento: o container de cron reexecuta em 15 min, e um erro
        # silencioso deixaria os centros de custo congelando sem ninguem notar.
        logger.exception('sincronizacao falhou')
        return 1
    finally:
        await engine.dispose()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
