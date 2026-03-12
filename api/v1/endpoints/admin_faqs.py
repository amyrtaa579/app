from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep, PaginationDep
from app.services.admin_faqs import FAQAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin/faqs", tags=["Admin FAQs"])

async def get_faq_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> FAQAdminService:
    return FAQAdminService(db, redis)

FAQServiceDep = Annotated[FAQAdminService, Depends(get_faq_service)]

@router.get("/", response_model=dict)
async def get_faqs(
    service: FAQServiceDep,
    current_admin: CurrentAdminDep,
    pagination: PaginationDep,
    category: Annotated[Optional[str], Query(description="Фильтр по категории")] = None
):
    """Получить список FAQ"""
    skip, limit = pagination
    
    if category:
        # Для админки не кэшируем по категориям
        items = await service.get_by_category(category)
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await service.get_multi(skip, limit)
    
    return {
        "data": [schemas.FAQAdmin.model_validate(f) for f in items],
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/search", response_model=List[schemas.FAQAdmin])
async def search_faqs(
    q: Annotated[str, Query(description="Поисковый запрос")],
    service: FAQServiceDep,
    current_admin: CurrentAdminDep
):
    """Поиск по FAQ"""
    items = await service.search(q)
    return items

@router.get("/{faq_id}", response_model=schemas.FAQAdmin)
async def get_faq(
    faq_id: Annotated[int, Path(description="ID вопроса")],
    service: FAQServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить FAQ по ID"""
    faq = await service.get_with_document(faq_id)
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    return faq

@router.post("/", response_model=schemas.FAQAdmin, status_code=status.HTTP_201_CREATED)
async def create_faq(
    faq_data: schemas.FAQAdminCreate,
    service: FAQServiceDep,
    current_admin: CurrentAdminDep
):
    """Создать новый FAQ"""
    return await service.create_with_document(faq_data)

@router.put("/{faq_id}", response_model=schemas.FAQAdmin)
async def update_faq(
    faq_id: Annotated[int, Path(description="ID вопроса")],
    faq_data: schemas.FAQAdminUpdate,
    service: FAQServiceDep,
    current_admin: CurrentAdminDep
):
    """Обновить FAQ"""
    faq = await service.update_with_document(faq_id, faq_data)
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    return faq

@router.delete("/{faq_id}", response_model=schemas.SuccessResponse)
async def delete_faq(
    faq_id: Annotated[int, Path(description="ID вопроса")],
    service: FAQServiceDep,
    current_admin: CurrentAdminDep
):
    """Удалить FAQ"""
    success = await service.delete(faq_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    return {"message": "FAQ deleted successfully", "id": faq_id}