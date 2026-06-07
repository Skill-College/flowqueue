"""Application configuration loaded from environment variables (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — must use the asyncpg driver, e.g.
    # postgresql+asyncpg://user:pass@host:5432/db
    database_url: str = "postgresql+asyncpg://flow:flow@localhost:5432/flowqueue"

    # Security
    secret_key: str = "change-me-in-prod"
    api_key_header: str = "Authorization"

    # JWT auth
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    refresh_cookie_name: str = "fq_refresh"
    cookie_secure: bool = False  # set True in production (HTTPS)
    cookie_samesite: str = "lax"

    # CORS (comma-separated origins for the Vite dev server). "*" allows all.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Logging
    log_level: str = "INFO"

    # Workers
    worker_concurrency: int = 4
    run_workers: bool = False

    # Replay rate limiting (messages per second)
    replay_rate_limit: int = 100

    @property
    def sync_database_url(self) -> str:
        """asyncpg URL is fine for Alembic too (we run async migrations)."""
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse cors_origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
