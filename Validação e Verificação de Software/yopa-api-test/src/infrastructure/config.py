"""
Global application settings.
Loads environment variables via Pydantic BaseSettings and exposes `settings` as the single access point.
AUTH_MODE controls the authentication mechanism: "standalone" uses Bearer {agent_id}.{secret};
"internal" expects X-Internal-Token + X-Agent-Id injected by the Yopa Proxy.
"""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_VERSION: str = "0.1.0"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT: int = 30
    APP_NAME: str = "AI-ChatBot"
    RUN_MODE: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATA_PATH: str = "./data"
    LOG_LEVEL: str = "INFO"
    REDIS_URL: str = "redis://localhost:6379"
    SESSION_TTL: int = 86400
    STORAGE_TYPE: str = "local"
    DATABASE_URL: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    WEBHOOK_URL: str = ""
    ANALYZER_LANGUAGES: list[str] = ["en"]
    SQL_ENCRYPTION_KEY: str = ""
    SQL_ALLOWED_DIALECTS: list[str] = ["postgresql", "mysql", "sqlite"]
    SQL_QUERY_TIMEOUT: int = 10
    SQL_MAX_ROWS: int = 50
    MAX_TOOL_ROUNDS: int = 5
    AUTH_MODE: str = "standalone"
    INTERNAL_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _check_internal_token(self) -> "Settings":
        if self.AUTH_MODE == "internal" and not self.INTERNAL_TOKEN:
            raise ValueError(
                "AUTH_MODE=internal requires INTERNAL_TOKEN to be set. "
                "Set INTERNAL_TOKEN in your .env or switch to AUTH_MODE=standalone."
            )
        return self


settings = Settings()
