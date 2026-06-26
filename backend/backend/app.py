import logging
import warnings

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler  # noqa: PLC2701
from slowapi.errors import RateLimitExceeded

from backend.core.limiter import limiter
from backend.core.settings import Settings
from backend.routers.associacoes import (
    router_assoc_contrato,
    router_assoc_eletronico,
)
from backend.routers.audit_log import router_audit_log
from backend.routers.auth import router_auth
from backend.routers.cessao import router_cessao
from backend.routers.contratos import router_contratos
from backend.routers.eletronicos import router_eletronicos
from backend.routers.localizacao import router_localizacoes
from backend.routers.marca import router_marcas
from backend.routers.modelo import router_modelos
from backend.routers.solicitacoes import router_solicitacoes
from backend.routers.tipo_eletronico import router_tipos_eletronico
from backend.routers.user import router_user

# Logging básico em formato estruturado-leve.
# Em produção, redirecione stdout para um agregador (Loki, CloudWatch, etc.).
# slowapi 0.1.9 usa asyncio.iscoroutinefunction (deprecated no Py 3.14+).
# Remover quando o slowapi lançar uma versão com inspect.iscoroutinefunction.
warnings.filterwarnings(
    'ignore',
    message="'asyncio.iscoroutinefunction' is deprecated",
    category=DeprecationWarning,
    module='slowapi',
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        '%(asctime)s [%(levelname)s] %(name)s - '
        '%(message)s'
    ),
)
logger = logging.getLogger('invcontrol')

settings = Settings()

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded, _rate_limit_exceeded_handler
)

# CORS — origens vêm do .env (separadas por vírgula).
_origins = [
    o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# GZip para responses ≥ 1 KB — listagens ficam ~70% menores.
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    """Cabeçalhos de segurança em todas as respostas."""
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = (
        'geolocation=(), microphone=(), camera=()'
    )
    return response


app.include_router(router_user)
app.include_router(router_eletronicos)
app.include_router(router_contratos)
app.include_router(router_assoc_contrato)
app.include_router(router_assoc_eletronico)
app.include_router(router_solicitacoes)
app.include_router(router_cessao)
app.include_router(router_tipos_eletronico)
app.include_router(router_localizacoes)
app.include_router(router_marcas)
app.include_router(router_modelos)
app.include_router(router_audit_log)
app.include_router(router_auth)

logger.info('app started — debug=%s, origins=%s', settings.DEBUG, _origins)
