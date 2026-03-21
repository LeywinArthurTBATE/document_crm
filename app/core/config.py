from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"  # lax | strict | none
    COOKIE_DOMAIN: str | None = None
    COOKIE_MAX_AGE: int = 60 * 60 * 24
    model_config = SettingsConfigDict(
        env_file=".env",
    )


settings = Settings()