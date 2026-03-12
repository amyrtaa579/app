from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep, PaginationDep
from app.services.admin_documents import DocumentAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin/documents", tags=["Admin Documents"])

async def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> DocumentAdminService:
    return DocumentAdminService(db, redis)

DocumentServiceDep = Annotated[DocumentAdminService, Depends(get_document_service)]

@router.get("/", response_model=dict)
async def get_documents(
    service: DocumentServiceDep,
    current_admin: CurrentAdminDep,
    pagination: PaginationDep,
    specialty_id: Annotated[Optional[int], Query(description="Фильтр по специальности")] = None
):
    """Получить список документов"""
    skip, limit = pagination
    
    if specialty_id:
        items, total = await service.get_by_specialty(specialty_id, skip, limit)
    else:
        items, total = await service.get_multi(skip, limit)
    
    return {
        "data": [schemas.DocumentAdmin.model_validate(d) for d in items],
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/{document_id}", response_model=schemas.DocumentAdmin)
async def get_document(
    document_id: Annotated[int, Path(description="ID документа")],
    service: DocumentServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить документ по ID"""
    document = await service.get_with_specialties(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.post("/", response_model=schemas.DocumentAdmin, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: schemas.DocumentAdminCreate,
    service: DocumentServiceDep,
    current_admin: CurrentAdminDep
):
    """Создать новый документ"""
    try:
        document = await service.create_with_specialties(document_data)
        return document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{document_id}", response_model=schemas.DocumentAdmin)
async def update_document(
    document_id: Annotated[int, Path(description="ID документа")],
    document_data: schemas.DocumentAdminUpdate,
    service: DocumentServiceDep,
    current_admin: CurrentAdminDep
):
    """Обновить документ"""
    document = await service.update_with_specialties(document_id, document_data)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.delete("/{document_id}", response_model=schemas.SuccessResponse)
async def delete_document(
    document_id: Annotated[int, Path(description="ID документа")],
    service: DocumentServiceDep,
    current_admin: CurrentAdminDep
):
    """Удалить документ"""
    success = await service.delete(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return {"message": "Document deleted successfully", "id": document_id}