from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep, PaginationDep
from app.services.admin_specialties import SpecialtyAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin/specialties", tags=["Admin Specialties"])

async def get_specialty_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> SpecialtyAdminService:
    return SpecialtyAdminService(db, redis)

SpecialtyServiceDep = Annotated[SpecialtyAdminService, Depends(get_specialty_service)]

@router.get("/", response_model=dict)
async def get_specialties(
    service: SpecialtyServiceDep,
    current_admin: CurrentAdminDep,
    pagination: PaginationDep
):
    """Получить список специальностей (для админки)"""
    skip, limit = pagination
    items, total = await service.get_multi(skip, limit)
    
    return {
        "data": [schemas.SpecialtyAdmin.model_validate(s) for s in items],
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/{specialty_id}", response_model=schemas.SpecialtyAdmin)
async def get_specialty(
    specialty_id: Annotated[int, Path(description="ID специальности")],
    service: SpecialtyServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить детальную информацию о специальности"""
    specialty = await service.get_with_relations(specialty_id)
    if not specialty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specialty not found"
        )
    return specialty

@router.post("/", response_model=schemas.SpecialtyAdmin, status_code=status.HTTP_201_CREATED)
async def create_specialty(
    specialty_data: schemas.SpecialtyAdminCreate,
    service: SpecialtyServiceDep,
    current_admin: CurrentAdminDep
):
    """Создать новую специальность"""
    try:
        specialty = await service.create_with_relations(specialty_data, current_admin.id)
        return specialty
    except Exception as e:
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Specialty with this code already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{specialty_id}", response_model=schemas.SpecialtyAdmin)
async def update_specialty(
    specialty_id: Annotated[int, Path(description="ID специальности")],
    specialty_data: schemas.SpecialtyAdminUpdate,
    service: SpecialtyServiceDep,
    current_admin: CurrentAdminDep
):
    """Обновить существующую специальность"""
    specialty = await service.update_with_relations(specialty_id, specialty_data, current_admin.id)
    if not specialty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specialty not found"
        )
    return specialty

@router.delete("/{specialty_id}", response_model=schemas.SuccessResponse)
async def delete_specialty(
    specialty_id: Annotated[int, Path(description="ID специальности")],
    service: SpecialtyServiceDep,
    current_admin: CurrentAdminDep
):
    """Удалить специальность"""
    success = await service.delete(specialty_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specialty not found"
        )
    
    # Также удаляем файлы изображений
    # TODO: добавить удаление файлов из файловой системы
    
    return {"message": "Specialty deleted successfully", "id": specialty_id}