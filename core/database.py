from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
from typing import Optional

from app.core.config import settings

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,  # например: postgresql+asyncpg://user:pass@localhost/dbname
    echo=True,  # Логировать SQL запросы (для разработки)
    pool_size=20,  # Размер пула соединений
    max_overflow=10  # Максимальное количество дополнительных соединений
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Redis клиент (будет инициализирован в lifespan)
redis_client: Optional[redis.Redis] = None

async def get_db() -> AsyncSession:
    """Зависимость для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_redis() -> redis.Redis:
    """Зависимость для получения Redis клиента"""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client