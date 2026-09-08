from os.path import dirname, join

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = dirname(dirname(dirname(__file__)))


class Settings(BaseSettings):  # pragma: no cover
    ENGINE_ASYNC: str
    ENGINE_SYNC: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    # --- OIDC / Keycloak ---------------------------------------------
    # Quem emite token é o Keycloak; aqui só validamos, com a chave pública
    # dele. SECRET_KEY e expiração são assunto do IdP.
    OIDC_ISSUER: str

    # O `aud` do access token. Cuidado: por padrão o Keycloak emite
    # aud="account", NÃO o client_id — validar contra o client rejeitaria
    # todo token. O realm tem um audience mapper que injeta este valor.
    OIDC_AUDIENCE: str = 'inventario-api'

    # Grupo exigido para entrar neste sistema. Sem esta checagem o
    # provisionamento automático abriria o inventário para todo o realm.
    OIDC_REQUIRED_GROUP: str = '/apps/inventario'

    # A conta mestra: UM email, definido no infra/.env e propagado aos três
    # sistemas, que entra como Admin aqui sem precisar do `create_admin.py`.
    # Existe para não ser preciso manter três contas só para administrar.
    #
    # Não é papel do Keycloak nem grupo: ser admin do console do Keycloak não
    # dá poder nenhum aqui, e nenhum grupo concede isto. É só este endereço.
    # Vazio (o padrão) = não existe conta mestra.
    ADMIN_MESTRE_EMAIL: str = ''

    # --- Sincronizacao com a receita ----------------------------------
    # A receita e a dona dos centros de custo; este servico so os consome.
    RECEITA_API_URL: str = ''
    RECEITA_API_TOKEN: str = ''

    DEBUG: bool = False
    ALLOWED_ORIGINS: str = 'http://localhost:3000'

    model_config = SettingsConfigDict(
        env_file=join(BASE_DIR, '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    def database_url_async(self) -> str:
        return f'{self.ENGINE_ASYNC}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    def database_url_sync(self) -> str:
        return f'{self.ENGINE_SYNC}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def oidc_jwks_url(self) -> str:
        return f"{self.OIDC_ISSUER.rstrip('/')}/protocol/openid-connect/certs"

    @property
    def oidc_authorization_url(self) -> str:
        return f"{self.OIDC_ISSUER.rstrip('/')}/protocol/openid-connect/auth"

    @property
    def oidc_token_url(self) -> str:
        return f"{self.OIDC_ISSUER.rstrip('/')}/protocol/openid-connect/token"
