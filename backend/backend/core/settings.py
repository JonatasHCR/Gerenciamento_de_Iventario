from os.path import dirname, join

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = dirname(dirname(dirname(__file__)))


class Settings(BaseSettings):
    ENGINE_ASYNC: str
    ENGINE_SYNC: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    model_config = SettingsConfigDict(
        env_file=join(BASE_DIR, '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    def database_url_async(self) -> str:
        return f'{self.ENGINE_ASYNC}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    def database_url_sync(self) -> str:
        return f'{self.ENGINE_SYNC}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
