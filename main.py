from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.middleware.logging_middleware import LoggingMiddleware, UserActionMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up...")
    yield
    # Shutdown
    print("👋 Shutting down...")

# Создаем FastAPI приложение
app = FastAPI(
    title="TPGK Bot API",
    description="API для чат-бота приемной комиссии ТПГК",
    version="1.0.0",
    lifespan=lifespan
)

# Добавляем middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(UserActionMiddleware)

# Монтируем статические файлы
app.mount(
    settings.STATIC_URL,
    StaticFiles(directory=settings.STATIC_FILES_DIR),
    name="static"
)

# Подключаем все API роуты
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "TPGK Bot API",
        "docs": "/docs",
        "static_url": settings.STATIC_URL
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}