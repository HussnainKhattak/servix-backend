from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App Info
    APP_NAME: str = "Servix Backend API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "insecure-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = ""
    POSTGRESS_URI: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Marketplace Parameters
    PLATFORM_FEE_PERCENTAGE: float = 5.0
    ESCROW_AUTO_RELEASE_DAYS: int = 3
    DEFAULT_SEARCH_RADIUS_MILES: float = 15.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def async_database_url(self) -> str:
        """
        Returns an asyncpg-compatible connection string for SQLAlchemy 2.0.
        Converts postgresql:// to postgresql+asyncpg:// and cleans incompatible parameters.
        """
        raw_url = self.DATABASE_URL or self.POSTGRESS_URI
        if not raw_url:
            return "sqlite+aiosqlite:///./servix_test.db"

        # Replace postgresql:// or postgres:// with postgresql+asyncpg://
        url = raw_url.strip().strip('"').strip("'")
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)

        # Remove query params that must be passed via connect_args for asyncpg
        import re
        # Remove channel_binding
        url = re.sub(r"[?&]channel_binding=[^&]*", "", url)
        # Remove sslmode / ssl (we pass ssl="require" via connect_args)
        url = re.sub(r"[?&]sslmode=[^&]*", "", url)
        url = re.sub(r"[?&]ssl=[^&]*", "", url)
        # Clean up dangling ? or leading &
        url = re.sub(r"\?&", "?", url)
        url = re.sub(r"\?$", "", url)
        if "?" not in url and "&" in url:
            url = url.replace("&", "?", 1)

        return url

    @property
    def sync_database_url(self) -> str:
        """
        Returns a sync psycopg2-compatible connection string for Alembic.
        """
        raw_url = self.DATABASE_URL or self.POSTGRESS_URI
        if not raw_url:
            return "sqlite:///./servix_test.db"
        url = raw_url.strip().strip('"').strip("'")
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url


settings = Settings()
