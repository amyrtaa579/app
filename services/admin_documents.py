from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from app.models import Document, Specialty, document_specialty
from app.schemas import admin as schemas
from app.services.base_crud import BaseCRUDService
from app.services.file_service import file_service

class DocumentAdminService(BaseCRUDService[
    Document,
    schemas.DocumentAdminCreate,
    schemas.DocumentAdminUpdate
]):
    """Сервис для управления документами"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=Document,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:document",
            cache_ttl=1800
        )
    
    async def create_with_specialties(
        self,
        schema: schemas.DocumentAdminCreate
    ) -> Document:
        """Создание документа с привязкой к специальностям"""
        
        # Создаем документ
        document_data = schema.model_dump(exclude={"specialty_ids"})
        document = Document(**document_data)
        self.db.add(document)
        await self.db.flush()
        
        # Привязываем к специальностям
        if schema.specialty_ids:
            # Получаем специальности
            result = await self.db.execute(
                select(Specialty).where(Specialty.id.in_(schema.specialty_ids))
            )
            specialties = result.scalars().all()
            document.specialties.extend(specialties)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        # Инвалидируем кэш
        await self._invalidate_cache()
        
        return document
    
    async def get_with_specialties(self, id: int) -> Optional[Document]:
        """Получение документа со связанными специальностями"""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == id)
            .options(selectinload(Document.specialties))
        )
        return result.scalar_one_or_none()
    
    async def update_with_specialties(
        self,
        id: int,
        schema: schemas.DocumentAdminUpdate
    ) -> Optional[Document]:
        """Обновление документа с привязкой к специальностям"""
        
        document = await self.get_with_specialties(id)
        if not document:
            return None
        
        old_file_url = document.file_url
        
        # Обновляем основные поля
        update_data = schema.model_dump(exclude={"specialty_ids"}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(document, field, value)
        
        # Обновляем привязку к специальностям
        if schema.specialty_ids is not None:
            # Очищаем текущие связи
            document.specialties = []
            
            # Добавляем новые
            if schema.specialty_ids:
                result = await self.db.execute(
                    select(Specialty).where(Specialty.id.in_(schema.specialty_ids))
                )
                specialties = result.scalars().all()
                document.specialties.extend(specialties)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        # Если файл изменился, удаляем старый
        if old_file_url != document.file_url and old_file_url:
            file_service.delete_file_by_url(old_file_url)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        
        return document
    
    async def delete(self, id: int) -> bool:
        """Удаление документа с физическим удалением файла"""
        document = await self.get(id)
        if not document:
            return False
        
        # Сохраняем URL файла для удаления
        file_url = document.file_url
        
        # Удаляем из БД
        await self.db.delete(document)
        await self.db.commit()
        
        # Удаляем файл физически
        if file_url:
            file_service.delete_file_by_url(file_url)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        
        return True
    
    async def get_by_specialty(
        self,
        specialty_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Document], int]:
        """Получение документов по специальности"""
        
        query = select(Document).where(
            Document.specialties.any(id=specialty_id),
            Document.is_active == True
        )
        
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        
        query = query.order_by(Document.title).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return items, total