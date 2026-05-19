from typing import Literal

from pydantic import BaseModel, EmailStr, Field

MIN_SENHA_LEN = 8


class UserCreate(BaseModel):
    nome: str = Field(..., min_length=1, description='Nome do usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    senha: str = Field(
        ...,
        min_length=MIN_SENHA_LEN,
        description=f'Senha do usuário (mínimo {MIN_SENHA_LEN} caracteres)',
    )
    tipo: Literal[
        'Gestor', 'Subgestor', 'Funcionario', 'Admin', 'Tecnico_TI'
    ] = Field(..., description='Tipo do usuário')


class UserUpdate(BaseModel):
    nome: str | None = Field(
        None, min_length=1, description='Nome do usuário'
    )
    email: EmailStr | None = Field(None, description='Email do usuário')
    senha: str | None = Field(
        None,
        min_length=MIN_SENHA_LEN,
        description=(
            f'Senha do usuário (mínimo {MIN_SENHA_LEN} caracteres). '
            'Vazio = manter atual.'
        ),
    )
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
