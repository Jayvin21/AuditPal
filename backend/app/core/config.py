from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AuditPal API"
    environment: str = "development"
    database_url: str = "sqlite:///./auditpal.db"
    upload_dir: str = "uploads"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
