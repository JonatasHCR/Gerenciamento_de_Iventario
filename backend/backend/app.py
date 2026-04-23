from fastapi import FastAPI

from backend.routers.contratos import router_contratos
from backend.routers.eletronicos import router_eletronicos
from backend.routers.user import router_user

app = FastAPI()

app.include_router(router_user)
app.include_router(router_eletronicos)
app.include_router(router_contratos)
