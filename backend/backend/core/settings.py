from os.path import dirname, join

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = dirname(dirname(dirname(__file__)))
load_dotenv()


class Settings(BaseSettings):
    ENGINE: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    model_config = SettingsConfigDict(
        env_file=join(BASE_DIR, '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    def database_url(self) -> str:
        return f'{self.ENGINE}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
