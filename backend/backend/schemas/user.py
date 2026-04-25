from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    nome: str = Field(..., description='Nome do usuário')
    username: str = Field(..., description='Nome de usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    senha: str = Field(..., description='Senha do usuário')
    tipo: str = Field(..., description='Tipo do usuário')


class UserRead(BaseModel):
    id: int = Field(..., description='ID do usuário')
    nome: str = Field(..., description='Nome do usuário')
    username: str = Field(..., description='Nome de usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    tipo: str = Field(..., description='Tipo do usuário')


class UserList(BaseModel):
    users: list[UserRead] = Field(..., description='Lista de usuários')
