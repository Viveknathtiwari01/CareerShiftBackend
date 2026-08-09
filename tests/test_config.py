import pytest

from app.core import config as config_module
from app.core.config import Settings, validate_production_settings


def test_effective_app_public_url_prefers_explicit_value():
    settings = Settings(
        ENVIRONMENT="production",
        DB_HOST="db",
        DB_PORT=5432,
        DB_USER="user",
        DB_PASSWORD="pass",
        DB_NAME="careershift",
        SECRET_KEY="x" * 32,
        APP_PUBLIC_URL="https://app.example.com",
        BACKEND_CORS_ORIGINS=["https://other.example.com"],
    )
    assert settings.effective_app_public_url == "https://app.example.com"


def test_database_url_normalizes_render_postgres_url():
    settings = Settings(
        ENVIRONMENT="production",
        DB_CONNECTION_URL="postgresql://user:pass@dpg-abc-a/dbname",
        SECRET_KEY="x" * 32,
    )
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@dpg-abc-a/dbname"


def test_supabase_pooler_connect_args_enable_ssl_and_disable_statement_cache():
    import ssl

    settings = Settings(
        ENVIRONMENT="production",
        DB_HOST="aws-0-ap-northeast-1.pooler.supabase.com",
        DB_PORT=6543,
        DB_USER="postgres.project",
        DB_PASSWORD="secret",
        DB_NAME="postgres",
        SECRET_KEY="x" * 32,
    )
    args = settings.database_connect_args
    assert args["statement_cache_size"] == 0
    assert isinstance(args["ssl"], ssl.SSLContext)


def test_effective_app_public_url_falls_back_to_https_cors_origin():
    settings = Settings(
        ENVIRONMENT="production",
        DB_HOST="db",
        DB_PORT=5432,
        DB_USER="user",
        DB_PASSWORD="pass",
        DB_NAME="careershift",
        SECRET_KEY="x" * 32,
        BACKEND_CORS_ORIGINS=["https://app.example.com"],
    )
    assert settings.effective_app_public_url == "https://app.example.com"


def test_validate_production_settings_allows_cors_fallback_for_public_url(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "settings",
        Settings(
            ENVIRONMENT="production",
            DB_HOST="db",
            DB_PORT=5432,
            DB_USER="user",
            DB_PASSWORD="pass",
            DB_NAME="careershift",
            SECRET_KEY="x" * 32,
            BACKEND_CORS_ORIGINS=["https://app.example.com"],
            SMTP_HOST="smtp.example.com",
            SMTP_USER="noreply@example.com",
            SMTP_PASSWORD="secret",
            EMAILS_FROM_EMAIL="noreply@example.com",
            ANTHROPIC_API_KEY="sk-ant-test",
            REPORT_READY_EMAIL_ENABLED=True,
        ),
    )

    validate_production_settings()


def test_validate_production_settings_blocks_missing_smtp_and_anthropic(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "settings",
        Settings(
            ENVIRONMENT="production",
            DB_HOST="db",
            DB_PORT=5432,
            DB_USER="user",
            DB_PASSWORD="pass",
            DB_NAME="careershift",
            SECRET_KEY="x" * 32,
            BACKEND_CORS_ORIGINS=["https://app.example.com"],
            APP_PUBLIC_URL="https://app.example.com",
            SMTP_HOST=None,
            SMTP_USER=None,
            SMTP_PASSWORD=None,
            EMAILS_FROM_EMAIL=None,
            ANTHROPIC_API_KEY=None,
        ),
    )

    with pytest.raises(RuntimeError, match="SMTP"):
        validate_production_settings()
