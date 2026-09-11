from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Criação de usuário por um Admin. Sem senha: quem guarda credencial é o
    Keycloak, e o caminho normal é o provisionamento automático no primeiro
    login válido."""

    nome: str = Field(..., min_length=1, description='Nome do usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    tipo: Literal[
        'Gestor', 'Subgestor', 'Funcionario', 'Admin', 'Tecnico_TI'
    ] = Field(..., description='Tipo do usuário')


class UserUpdate(BaseModel):
    """Só o `tipo`. Nome e email vêm do Keycloak.

    `extra='forbid'` de propósito: descartar em silêncio devolveria 200 sem ter
    mudado nada, e quem chamou ficaria achando que mudou.
    """

    model_config = ConfigDict(extra='forbid')

    tipo: Literal[
        'Gestor', 'Subgestor', 'Funcionario', 'Admin', 'Tecnico_TI'
    ] | None = Field(None, description='Tipo do usuário')


class UserRead(BaseModel):
    id: int = Field(..., description='ID do usuário')
    nome: str = Field(..., description='Nome do usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    tipo: Literal[
        'Gestor', 'Subgestor', 'Funcionario', 'Admin', 'Tecnico_TI'
    ] = Field(..., description='Tipo do usuário')


class UserList(BaseModel):
    users: list[UserRead] = Field(..., description='Lista de usuários')
