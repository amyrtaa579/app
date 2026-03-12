from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis
import json

from app.models import About, AdmissionInfo, Admin
from app.schemas import admin as schemas

class AboutAdminService:
    """Сервис для управления информацией о колледже"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    async def get(self) -> Optional[About]:
        """Получение информации о колледже"""
        cache_key = "about"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return About(**data)
        
        result = await self.db.execute(
            select(About).where(About.id == 1)
        )
        about = result.scalar_one_or_none()
        
        if about:
            from sqlalchemy.inspection import inspect
            data = {c.key: getattr(about, c.key) for c in inspect(about).mapper.column_attrs}
            await self.redis.setex(cache_key, 3600, json.dumps(data, default=str))
        
        return about
    
    async def update(
        self,
        schema: schemas.AboutAdminUpdate,
        admin_id: int
    ) -> About:
        """Обновление информации о колледже"""
        
        about = await self.get()
        
        if about:
            about.content = schema.content
            about.updated_by = admin_id
        else:
            about = About(
                id=1,
                content=schema.content,
                updated_by=admin_id
            )
            self.db.add(about)
        
        await self.db.commit()
        await self.db.refresh(about)
        
        # Инвалидируем кэш
        await self.redis.delete("about")
        
        return about

class AdmissionInfoAdminService:
    """Сервис для управления информацией о приеме"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    async def get_current(self) -> Optional[AdmissionInfo]:
        """Получение текущей информации о приеме"""
        cache_key = "admission:current"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return AdmissionInfo(**data)
        
        result = await self.db.execute(
            select(AdmissionInfo)
            .where(AdmissionInfo.is_current == True)
            .order_by(AdmissionInfo.year.desc())
            .limit(1)
        )
        admission = result.scalar_one_or_none()
        
        if admission:
            from sqlalchemy.inspection import inspect
            data = {c.key: getattr(admission, c.key) for c in inspect(admission).mapper.column_attrs}
            await self.redis.setex(cache_key, 3600, json.dumps(data, default=str))
        
        return admission
    
    async def get_by_year(self, year: int) -> Optional[AdmissionInfo]:
        """Получение информации о приеме за год"""
        cache_key = f"admission:{year}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return AdmissionInfo(**data)
        
        result = await self.db.execute(
            select(AdmissionInfo).where(AdmissionInfo.year == year)
        )
        admission = result.scalar_one_or_none()
        
        if admission:
            from sqlalchemy.inspection import inspect
            data = {c.key: getattr(admission, c.key) for c in inspect(admission).mapper.column_attrs}
            await self.redis.setex(cache_key, 3600, json.dumps(data, default=str))
        
        return admission
    
    async def create(
        self,
        schema: schemas.AdmissionInfoAdminCreate,
        admin_id: int
    ) -> AdmissionInfo:
        """Создание информации о приеме"""
        
        # Если это текущий год, сбрасываем флаг у других
        if schema.is_current:
            await self.db.execute(
                update(AdmissionInfo)
                .where(AdmissionInfo.is_current == True)
                .values(is_current=False)
            )
        
        admission = AdmissionInfo(
            **schema.model_dump(),
            updated_by=admin_id
        )
        self.db.add(admission)
        await self.db.commit()
        await self.db.refresh(admission)
        
        # Инвалидируем кэш
        await self.redis.delete("admission:*")
        
        return admission
    
    async def update(
        self,
        id: int,
        schema: schemas.AdmissionInfoAdminUpdate,
        admin_id: int
    ) -> Optional[AdmissionInfo]:
        """Обновление информации о приеме"""
        
        result = await self.db.execute(
            select(AdmissionInfo).where(AdmissionInfo.id == id)
        )
        admission = result.scalar_one_or_none()
        
        if not admission:
            return None
        
        # Если устанавливаем текущим, сбрасываем у других
        if schema.is_current and not admission.is_current:
            await self.db.execute(
                update(AdmissionInfo)
                .where(AdmissionInfo.is_current == True)
                .values(is_current=False)
            )
        
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(admission, field, value)
        
        admission.updated_by = admin_id
        
        await self.db.commit()
        await self.db.refresh(admission)
        
        # Инвалидируем кэш
        await self.redis.delete("admission:*")
        
        return admission
    
    async def delete(self, id: int) -> bool:
        """Удаление информации о приеме"""
        result = await self.db.execute(
            select(AdmissionInfo).where(AdmissionInfo.id == id)
        )
        admission = result.scalar_one_or_none()
        
        if not admission:
            return False
        
        await self.db.delete(admission)
        await self.db.commit()
        
        # Инвалидируем кэш
        await self.redis.delete("admission:*")
        
        return True