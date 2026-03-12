from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from redis.asyncio import Redis

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseCRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый CRUD сервис с кэшированием"""
    
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
        redis: Redis,
        cache_key_prefix: str,
        cache_ttl: int = 3600
    ):
        self.model = model
        self.db = db
        self.redis = redis
        self.cache_key_prefix = cache_key_prefix
        self.cache_ttl = cache_ttl
    
    async def _invalidate_cache(self, id: Optional[int] = None):
        """Инвалидация кэша"""
        pattern = f"{self.cache_key_prefix}:*"
        if id:
            pattern = f"{self.cache_key_prefix}:{id}:*"
        
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
    
    async def create(self, schema: CreateSchemaType, **extra_data) -> ModelType:
        """Создание записи"""
        data = schema.model_dump(exclude_unset=True)
        data.update(extra_data)
        
        db_obj = self.model(**data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        # Инвалидируем кэш списка
        await self._invalidate_cache()
        
        return db_obj
    
    async def get(self, id: int) -> Optional[ModelType]:
        """Получение записи по ID"""
        # Пробуем из кэша
        cache_key = f"{self.cache_key_prefix}:{id}:item"
        cached = await self.redis.get(cache_key)
        
        if cached:
            import json
            data = json.loads(cached)
            return self.model(**data)
        
        # Из базы
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        obj = result.scalar_one_or_none()
        
        # Кэшируем
        if obj:
            import json
            from sqlalchemy.inspection import inspect
            data = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(data, default=str))
        
        return obj
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[ModelType], int]:
        """Получение списка записей с пагинацией"""
        # Ключ кэша с учетом фильтров
        filter_str = "_".join(f"{k}:{v}" for k, v in (filters or {}).items())
        cache_key = f"{self.cache_key_prefix}:list:{skip}:{limit}:{filter_str}"
        
        cached = await self.redis.get(cache_key)
        if cached:
            import json
            data = json.loads(cached)
            # Здесь нужно будет воссоздать объекты, но для простоты вернем данные
            return data["items"], data["total"]
        
        # Строим запрос
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        # Общее количество
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        
        # Данные с пагинацией
        query = query.order_by(self.model.id).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Кэшируем
        import json
        from sqlalchemy.inspection import inspect
        
        items_data = []
        for item in items:
            data = {c.key: getattr(item, c.key) for c in inspect(item).mapper.column_attrs}
            items_data.append(data)
        
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps({"items": items_data, "total": total}, default=str)
        )
        
        return items, total
    
    async def update(self, id: int, schema: UpdateSchemaType) -> Optional[ModelType]:
        """Обновление записи"""
        obj = await self.get(id)
        if not obj:
            return None
        
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        
        await self.db.commit()
        await self.db.refresh(obj)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        
        return obj
    
    async def delete(self, id: int) -> bool:
        """Удаление записи"""
        obj = await self.get(id)
        if not obj:
            return False
        
        await self.db.delete(obj)
        await self.db.commit()
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        
        return True