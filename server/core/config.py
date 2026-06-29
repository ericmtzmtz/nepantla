from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Nepantla"
    VERSION: str = "2.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database - read from individual .env vars, build URL dynamically
    DB_URL: str = "localhost"
    DB_USER=nepantla
DB_PASS=nepantla2026!*
DB=nepantla
    SQL_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASS)}@{self.DB_URL}:5432/{self.DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:  # noqa: N802
        return f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASS)}@{self.DB_URL}:5432/{self.DB}"

    # Security
    ENCRYPTION_KEY: str = ""
    UNIFIED_API_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limit Defaults
    DEFAULT_RPM_LIMIT: int = 30
    DEFAULT_RPD_LIMIT: int = 1000
    DEFAULT_TPM_LIMIT: int = 100000
    DEFAULT_TPD_LIMIT: int = 1000000

    # Router
    PENALTY_PER_429: int = 3
    MAX_PENALTY: int = 10
    DECAY_INTERVAL_MS: int = 120000
    DECAY_AMOUNT: int = 1
    STICKY_SESSION_TTL_MINUTES: int = 30

    # Analytics
    ANALYTICS_BUFFER_SECONDS: int = 60
    ANALYTICS_BUFFER_MAX_ITEMS: int = 1000
    CLEANUP_RETENTION_DAYS: int = 30

    # Health
    HEALTH_CHECK_INTERVAL_MINUTES: int = 5
    HEALTH_MAX_FAILURES: int = 3

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
