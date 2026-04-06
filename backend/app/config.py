from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://finance:finance123@localhost:5432/finance_db"
    DATABASE_URL_SYNC: str = "postgresql://finance:finance123@localhost:5432/finance_db"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 horas
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "/app/uploads"

    model_config = {"env_file": ".env"}


settings = Settings()
