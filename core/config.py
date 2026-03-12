from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
from pathlib import Path

class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost/tpgk_bot",
        validation_alias="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = 10
    
    # JWT
    SECRET_KEY: str = Field(..., min_length=32, validation_alias="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 часа
    
    # Администратор по умолчанию
    DEFAULT_ADMIN_LOGIN: str = Field(default="admin@tpgk.ru", validation_alias="DEFAULT_ADMIN_LOGIN")
    DEFAULT_ADMIN_PASSWORD: str = Field(..., min_length=8, validation_alias="DEFAULT_ADMIN_PASSWORD")
    DEFAULT_ADMIN_NAME: str = Field(default="Главный администратор", validation_alias="DEFAULT_ADMIN_NAME")
    
    # Настройки статики
    STATIC_FILES_DIR: Path = Field(default="/home/tpgk/static", validation_alias="STATIC_FILES_DIR")
    STATIC_URL: str = "/static"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # Разрешенные типы файлов
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_DOCUMENT_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    
    # Настройки парсера
    PARSER_TIMEOUT: int = 30
    PARSER_MAX_RETRIES: int = 3
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/home/tpgk/logs/app.log"
    ACCESS_LOG_FILE: str = "/home/tpgk/logs/access.log"
    ERROR_LOG_FILE: str = "/home/tpgk/logs/error.log"
    
    # Настройки Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", validation_alias="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", validation_alias="CELERY_RESULT_BACKEND")
    
    # Хост и порт для запуска
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

settings = Settings()