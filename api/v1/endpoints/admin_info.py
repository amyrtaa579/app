from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep
from app.services.admin_info import AboutAdminService, AdmissionInfoAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin", tags=["Admin Info"])

# ========== О КОЛЛЕДЖЕ ==========

@router.get("/about", response_model=schemas.AboutAdmin)
async def get_about(
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить информацию о колледже"""
    service = AboutAdminService(db, redis)
    about = await service.get()
    if not about:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="About information not found"
        )
    return about

@router.put("/about", response_model=schemas.AboutAdmin)
async def update_about(
    about_data: schemas.AboutAdminUpdate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Обновить информацию о колледже"""
    service = AboutAdminService(db, redis)
    about = await service.update(about_data, current_admin.id)
    return about

# ========== ИНФОРМАЦИЯ О ПРИЕМЕ ==========

@router.get("/admission/current", response_model=schemas.AdmissionInfoAdmin)
async def get_current_admission(
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить текущую информацию о приеме"""
    service = AdmissionInfoAdminService(db, redis)
    admission = await service.get_current()
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission information not found"
        )
    return admission

@router.get("/admission/year/{year}", response_model=schemas.AdmissionInfoAdmin)
async def get_admission_by_year(
    year: Annotated[int, Path(description="Год набора")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить информацию о приеме за указанный год"""
    service = AdmissionInfoAdminService(db, redis)
    admission = await service.get_by_year(year)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission information not found"
        )
    return admission

@router.post("/admission", response_model=schemas.AdmissionInfoAdmin, status_code=status.HTTP_201_CREATED)
async def create_admission(
    admission_data: schemas.AdmissionInfoAdminCreate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Создать информацию о приеме"""
    service = AdmissionInfoAdminService(db, redis)
    return await service.create(admission_data, current_admin.id)

@router.put("/admission/{admission_id}", response_model=schemas.AdmissionInfoAdmin)
async def update_admission(
    admission_id: Annotated[int, Path(description="ID записи")],
    admission_data: schemas.AdmissionInfoAdminUpdate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Обновить информацию о приеме"""
    service = AdmissionInfoAdminService(db, redis)
    admission = await service.update(admission_id, admission_data, current_admin.id)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission information not found"
        )
    return admission

@router.delete("/admission/{admission_id}", response_model=schemas.SuccessResponse)
async def delete_admission(
    admission_id: Annotated[int, Path(description="ID записи")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Удалить информацию о приеме"""
    service = AdmissionInfoAdminService(db, redis)
    success = await service.delete(admission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission information not found"
        )
    return {"message": "Admission information deleted successfully", "id": admission_id}