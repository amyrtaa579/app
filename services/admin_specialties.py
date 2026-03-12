from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from app.models import Specialty, Reality, Fact
from app.schemas import admin as schemas
from app.services.base_crud import BaseCRUDService

class SpecialtyAdminService(BaseCRUDService[
    Specialty,
    schemas.SpecialtyAdminCreate,
    schemas.SpecialtyAdminUpdate
]):
    """Сервис для управления специальностями"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=Specialty,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:specialty",
            cache_ttl=1800  # 30 минут для админки
        )
    
    async def create_with_relations(
        self,
        schema: schemas.SpecialtyAdminCreate,
        admin_id: int
    ) -> Specialty:
        """Создание специальности со всеми связями"""
        
        # Создаем специальность
        specialty_data = schema.model_dump(exclude={"realities", "facts"})
        specialty = Specialty(**specialty_data)
        self.db.add(specialty)
        await self.db.flush()  # Получаем ID
        
        # Добавляем realities
        for reality_data in schema.realities:
            reality = Reality(
                specialty_id=specialty.id,
                **reality_data.model_dump()
            )
            self.db.add(reality)
        
        # Добавляем facts
        for fact_data in schema.facts:
            fact = Fact(
                specialty_id=specialty.id,
                **fact_data.model_dump()
            )
            self.db.add(fact)
        
        await self.db.commit()
        await self.db.refresh(specialty)
        
        # Инвалидируем кэш
        await self._invalidate_cache()
        
        return specialty
    
    async def get_with_relations(self, id: int) -> Optional[Specialty]:
        """Получение специальности со всеми связями"""
        result = await self.db.execute(
            select(Specialty)
            .where(Specialty.id == id)
            .options(
                selectinload(Specialty.realities),
                selectinload(Specialty.facts)
            )
        )
        specialty = result.scalar_one_or_none()
        
        if specialty:
            # Сортируем
            specialty.realities.sort(key=lambda x: x.sort_order)
            specialty.facts.sort(key=lambda x: x.sort_order)
        
        return specialty
    
    async def update_with_relations(
        self,
        id: int,
        schema: schemas.SpecialtyAdminUpdate,
        admin_id: int
    ) -> Optional[Specialty]:
        """Обновление специальности со всеми связями"""
        
        specialty = await self.get_with_relations(id)
        if not specialty:
            return None
        
        # Обновляем основные поля
        update_data = schema.model_dump(exclude={"realities", "facts"}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(specialty, field, value)
        
        # Обновляем realities
        if schema.realities is not None:
            # Удаляем старые
            for reality in specialty.realities:
                await self.db.delete(reality)
            
            # Добавляем новые
            for reality_data in schema.realities:
                reality = Reality(
                    specialty_id=specialty.id,
                    **reality_data.model_dump()
                )
                self.db.add(reality)
        
        # Обновляем facts
        if schema.facts is not None:
            # Удаляем старые
            for fact in specialty.facts:
                await self.db.delete(fact)
            
            # Добавляем новые
            for fact_data in schema.facts:
                fact = Fact(
                    specialty_id=specialty.id,
                    **fact_data.model_dump()
                )
                self.db.add(fact)
        
        await self.db.commit()
        await self.db.refresh(specialty)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()  # Также сбрасываем список
        
        return specialty