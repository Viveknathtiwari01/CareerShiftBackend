from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_NAME: str = "CareerShift API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
        
    # Email / SMTP
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    ANTHROPIC_TEMPERATURE: float = 0.0
    # Used for models that reject temperature (e.g. claude-sonnet-5): low | medium | high
    ANTHROPIC_EFFORT: str = "low"
    APP_PUBLIC_URL: str = "http://localhost:5173"

    # Production hardening (Phase 8)
    COMPETENCY_PIPELINE_TIMEOUT_SECONDS: int = 600
    PIPELINE_STALE_AFTER_SECONDS: int = 900
    ASSESSMENT_START_RATE_LIMIT: int = 5
    ASSESSMENT_START_RATE_WINDOW_SECONDS: int = 3600
    REPORT_GENERATE_RATE_LIMIT: int = 10
    REPORT_GENERATE_RATE_WINDOW_SECONDS: int = 3600
    REPORT_READY_EMAIL_ENABLED: bool = True
    USE_CELERY: bool = False
    CELERY_BROKER_URL: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def email_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD and self.EMAILS_FROM_EMAIL)

    # Production hardening (Phase 8)
    COMPETENCY_PIPELINE_TIMEOUT_SECONDS: int = 600
    PIPELINE_STALE_AFTER_SECONDS: int = 900
    ASSESSMENT_START_RATE_LIMIT: int = 5
    ASSESSMENT_START_RATE_WINDOW_SECONDS: int = 3600
    REPORT_GENERATE_RATE_LIMIT: int = 10
    REPORT_GENERATE_RATE_WINDOW_SECONDS: int = 3600
    DEFAULT_RATE_LIMIT: int = 60
    DEFAULT_RATE_WINDOW_SECONDS: int = 60
    REPORT_READY_EMAIL_ENABLED: bool = True
    APP_PUBLIC_URL: str = "http://localhost:5173"
    USE_CELERY: bool = False
    CELERY_BROKER_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()


def validate_production_settings() -> None:
    if not settings.is_production:
        return
    missing: list[str] = []
    if not settings.email_configured:
        missing.append("SMTP (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAILS_FROM_EMAIL)")
    if not settings.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        raise RuntimeError(
            "Production startup blocked. Missing required settings: " + ", ".join(missing)
        )
