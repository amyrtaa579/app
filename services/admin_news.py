from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from datetime import datetime

from app.models import News, NewsImage
from app.schemas import admin as schemas
from app.services.base_crud import BaseCRUDService
from app.services.file_service import file_service

class NewsAdminService(BaseCRUDService[
    News,
    schemas.NewsAdminCreate,
    schemas.NewsAdminUpdate
]):
    """Сервис для управления новостями"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=News,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:news",
            cache_ttl=1800
        )
    
    async def create_with_images(
        self,
        schema: schemas.NewsAdminCreate
    ) -> News:
        """Создание новости с изображениями"""
        
        # Создаем новость
        news_data = schema.model_dump(exclude={"images"})
        news = News(**news_data)
        self.db.add(news)
        await self.db.flush()
        
        # Добавляем изображения
        for image_data in schema.images:
            image = NewsImage(
                news_id=news.id,
                **image_data.model_dump()
            )
            self.db.add(image)
        
        await self.db.commit()
        await self.db.refresh(news)
        
        # Инвалидируем кэш
        await self._invalidate_cache()
        await self.redis.delete("news:*")
        
        return news
    
    async def get_with_images(self, id: int) -> Optional[News]:
        """Получение новости с изображениями"""
        result = await self.db.execute(
            select(News)
            .where(News.id == id)
            .options(selectinload(News.images))
        )
        news = result.scalar_one_or_none()
        
        if news:
            news.images.sort(key=lambda x: x.sort_order)
        
        return news
    
    async def update_with_images(
        self,
        id: int,
        schema: schemas.NewsAdminUpdate
    ) -> Optional[News]:
        """Обновление новости с изображениями"""
        
        news = await self.get_with_images(id)
        if not news:
            return None
        
        # Сохраняем старые изображения для удаления
        old_images = list(news.images)
        
        # Обновляем основные поля
        update_data = schema.model_dump(exclude={"images"}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(news, field, value)
        
        # Обновляем изображения
        if schema.images is not None:
            # Удаляем старые
            for image in old_images:
                await self.db.delete(image)
                # Удаляем файлы
                if image.image_url:
                    file_service.delete_file_by_url(str(image.image_url))
            
            # Добавляем новые
            for image_data in schema.images:
                image = NewsImage(
                    news_id=news.id,
                    **image_data.model_dump()
                )
                self.db.add(image)
        
        await self.db.commit()
        await self.db.refresh(news)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        await self.redis.delete("news:*")
        
        return news
    
    async def delete(self, id: int) -> bool:
        """Удаление новости с удалением изображений"""
        news = await self.get_with_images(id)
        if not news:
            return False
        
        # Удаляем файлы изображений
        for image in news.images:
            if image.image_url:
                file_service.delete_file_by_url(str(image.image_url))
        
        # Удаляем из БД
        await self.db.delete(news)
        await self.db.commit()
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        await self.redis.delete("news:*")
        
        return True
    
    async def get_published(
        self,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[News], int]:
        """Получение опубликованных новостей"""
        
        query = select(News).where(News.is_published == True)
        
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        
        query = query.order_by(News.date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return items, total