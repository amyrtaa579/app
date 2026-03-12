#!/usr/bin/env python3
"""
Скрипт инициализации проекта:
- Создает структуру папок
- Инициализирует базу данных
- Создает первого администратора
"""
import asyncio
import os
from pathlib import Path
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Base, Admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_database_if_not_exists():
    """Создает базу данных, если она не существует"""
    try:
        # Подключаемся к postgres (системная БД)
        conn = await asyncpg.connect(
            user=settings.DATABASE_URL.split('://')[1].split('@')[0].split(':')[0],
            password=settings.DATABASE_URL.split('://')[1].split('@')[0].split(':')[1].split('/')[0],
            host=settings.DATABASE_URL.split('@')[1].split(':')[0],
            database='postgres'
        )
        
        # Проверяем существование БД
        db_name = settings.DATABASE_URL.split('/')[-1]
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if not result:
            logger.info(f"Creating database {db_name}...")
            await conn.execute(f'CREATE DATABASE {db_name}')
            logger.info("Database created successfully")
        
        await conn.close()
    except Exception as e:
        logger.error(f"Error creating database: {e}")

async def init_db():
    """Инициализирует базу данных"""
    logger.info("Creating database engine...")
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    logger.info("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Tables created successfully")
    
    # Создаем администратора по умолчанию
    async with engine.connect() as conn:
        from sqlalchemy import select
        
        result = await conn.execute(
            select(Admin).where(Admin.login == settings.DEFAULT_ADMIN_LOGIN)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            logger.info("Creating default admin...")
            admin = Admin(
                login=settings.DEFAULT_ADMIN_LOGIN,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                full_name=settings.DEFAULT_ADMIN_NAME
            )
            conn.add(admin)
            await conn.commit()
            logger.info("Default admin created")
        else:
            logger.info("Admin already exists")
    
    await engine.dispose()

async def create_directories():
    """Создает необходимые директории"""
    dirs = [
        settings.STATIC_FILES_DIR,
        settings.STATIC_FILES_DIR / "uploads",
        settings.STATIC_FILES_DIR / "uploads" / "images",
        settings.STATIC_FILES_DIR / "uploads" / "images" / "specialties",
        settings.STATIC_FILES_DIR / "uploads" / "images" / "facts",
        settings.STATIC_FILES_DIR / "uploads" / "images" / "news",
        settings.STATIC_FILES_DIR / "uploads" / "images" / "results",
        settings.STATIC_FILES_DIR / "uploads" / "documents",
        settings.STATIC_FILES_DIR / "uploads" / "documents" / "9_class",
        settings.STATIC_FILES_DIR / "uploads" / "documents" / "11_class",
        settings.STATIC_FILES_DIR / "uploads" / "documents" / "parents",
        Path("/home/tpgk/logs"),
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

async def main():
    """Главная функция инициализации"""
    logger.info("Starting project initialization...")
    
    # Создаем директории
    await create_directories()
    
    # Создаем базу данных
    await create_database_if_not_exists()
    
    # Инициализируем таблицы
    await init_db()
    
    logger.info("Project initialization completed!")

if __name__ == "__main__":
    asyncio.run(main())