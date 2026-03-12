import json
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.core.database import redis_client  # Импортируем клиент

CACHE_TTL_SPECIALTIES = 3600  # 1 час

async def get_specialty_with_details(db: AsyncSession, specialty_id: int) -> Optional[schemas.Specialty]:
    # 1. Пытаемся получить из кэша Redis
    if redis_client:
        cached_data = await redis_client.get(f"specialty:{specialty_id}")
        if cached_data:
            # Если нашли, возвращаем Pydantic модель из JSON
            return schemas.Specialty.model_validate_json(cached_data)

    # 2. Если в кэше нет, идем в базу
    result = await db.execute(
        select(models.Specialty)
        .where(models.Specialty.id == specialty_id)
        .options(
            selectinload(models.Specialty.realities),
            selectinload(models.Specialty.facts)
        )
    )
    specialty = result.scalar_one_or_none()
    
    # 3. Если нашли в БД, кладем в кэш
    if specialty and redis_client:
        specialty_pydantic = schemas.Specialty.model_validate(specialty)
        await redis_client.setex(
            f"specialty:{specialty_id}",
            CACHE_TTL_SPECIALTIES,
            specialty_pydantic.model_dump_json()
        )
    
    return specialty