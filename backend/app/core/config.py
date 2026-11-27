from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SEO Intelligence Engine"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://seo_admin:StrongLocalPassword123!@postgres:5432/seo_intelligence"
    REDIS_URL: str = "redis://redis:6379/0"

    CRAWLER_CONCURRENCY: int = 4
    CRAWLER_DOWNLOAD_DELAY: float = 1.5
    CRAWLER_MAX_DEPTH: int = 3
    CRAWLER_MAX_PAGES_PER_JOB: int = 10000
    CRAWLER_MAX_RESPONSE_BYTES: int = 5242880
    CELERY_WORKER_CONCURRENCY: int = 2

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    SECRET_KEY: str = "change-this-secret"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()