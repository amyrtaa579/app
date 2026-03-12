from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from app.models import FAQ, Document
from app.schemas import admin as schemas
from app.services.base_crud import BaseCRUDService

class FAQAdminService(BaseCRUDService[
    FAQ,
    schemas.FAQAdminCreate,
    schemas.FAQAdminUpdate
]):
    """Сервис для управления FAQ"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=FAQ,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:faq",
            cache_ttl=1800
        )
    
    async def create_with_document(
        self,
        schema: schemas.FAQAdminCreate
    ) -> FAQ:
        """Создание FAQ с привязкой к документу"""
        
        faq = FAQ(**schema.model_dump())
        self.db.add(faq)
        await self.db.commit()
        await self.db.refresh(faq)
        
        # Инвалидируем кэш
        await self._invalidate_cache()
        await self.redis.delete("faqs:*")
        
        return faq
    
    async def get_with_document(self, id: int) -> Optional[FAQ]:
        """Получение FAQ со связанным документом"""
        result = await self.db.execute(
            select(FAQ)
            .where(FAQ.id == id)
            .options(selectinload(FAQ.document))
        )
        return result.scalar_one_or_none()
    
    async def update_with_document(
        self,
        id: int,
        schema: schemas.FAQAdminUpdate
    ) -> Optional[FAQ]:
        """Обновление FAQ"""
        faq = await self.get(id)
        if not faq:
            return None
        
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(faq, field, value)
        
        await self.db.commit()
        await self.db.refresh(faq)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        await self.redis.delete("faqs:*")
        
        return faq
    
    async def search(self, query: str, limit: int = 10) -> List[FAQ]:
        """Поиск по вопросам и ответам"""
        result = await self.db.execute(
            select(FAQ)
            .where(
                or_(
                    FAQ.question.ilike(f"%{query}%"),
                    FAQ.answer.ilike(f"%{query}%")
                ),
                FAQ.is_active == True
            )
            .order_by(FAQ.sort_order)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_category(self, category: str) -> List[FAQ]:
        """Получение FAQ по категории"""
        cache_key = f"faqs:category:{category}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            import json
            data = json.loads(cached)
            return [FAQ(**item) for item in data]
        
        result = await self.db.execute(
            select(FAQ)
            .where(FAQ.category == category, FAQ.is_active == True)
            .order_by(FAQ.sort_order, FAQ.question)
        )
        faqs = result.scalars().all()
        
        # Кэшируем
        if faqs:
            import json
            from sqlalchemy.inspection import inspect
            items_data = []
            for item in faqs:
                data = {c.key: getattr(item, c.key) for c in inspect(item).mapper.column_attrs}
                items_data.append(data)
            await self.redis.setex(cache_key, 3600, json.dumps(items_data, default=str))
        
        return faqs