from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep, PaginationDep
from app.services.admin_news import NewsAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin/news", tags=["Admin News"])

async def get_news_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> NewsAdminService:
    return NewsAdminService(db, redis)

NewsServiceDep = Annotated[NewsAdminService, Depends(get_news_service)]

@router.get("/", response_model=dict)
async def get_news(
    service: NewsServiceDep,
    current_admin: CurrentAdminDep,
    pagination: PaginationDep,
    published_only: bool = Query(False, description="Только опубликованные")
):
    """Получить список новостей"""
    skip, limit = pagination
    
    if published_only:
        items, total = await service.get_published(skip, limit)
    else:
        items, total = await service.get_multi(skip, limit)
    
    return {
        "data": [schemas.NewsAdmin.model_validate(n) for n in items],
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/{news_id}", response_model=schemas.NewsAdmin)
async def get_news_detail(
    news_id: Annotated[int, Path(description="ID новости")],
    service: NewsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить новость с изображениями"""
    news = await service.get_with_images(news_id)
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    return news

@router.post("/", response_model=schemas.NewsAdmin, status_code=status.HTTP_201_CREATED)
async def create_news(
    news_data: schemas.NewsAdminCreate,
    service: NewsServiceDep,
    current_admin: CurrentAdminDep
):
    """Создать новую новость"""
    return await service.create_with_images(news_data)

@router.put("/{news_id}", response_model=schemas.NewsAdmin)
async def update_news(
    news_id: Annotated[int, Path(description="ID новости")],
    news_data: schemas.NewsAdminUpdate,
    service: NewsServiceDep,
    current_admin: CurrentAdminDep
):
    """Обновить новость"""
    news = await service.update_with_images(news_id, news_data)
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    return news

@router.delete("/{news_id}", response_model=schemas.SuccessResponse)
async def delete_news(
    news_id: Annotated[int, Path(description="ID новости")],
    service: NewsServiceDep,
    current_admin: CurrentAdminDep
):
    """Удалить новость"""
    success = await service.delete(news_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    return {"message": "News deleted successfully", "id": news_id}