from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from jwt import encode
from pwdlib import PasswordHash

from backend.core.settings import Settings


class Security:
    def __init__(self):
        self.password_hasher = PasswordHash.recommended()
        self.settings = Settings()

    def get_senha_hash(self, senha: str) -> str:
        return self.password_hasher.hash(senha)

    def verify_senha(self, senha: str, hashed_senha: str) -> bool:
        return self.password_hasher.verify(senha, hashed_senha)

    def get_access_token(self, data: dict) -> str:
        to_encode = data.copy()

        expire = datetime.now(tz=ZoneInfo('America/Sao_Paulo')) + timedelta(
            minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({'exp': expire})

        encoded_jwt = encode(
            to_encode,
            self.settings.SECRET_KEY,
            algorithm=self.settings.ALGORITHM,
        )

        return encoded_jwt
