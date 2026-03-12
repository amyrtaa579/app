from typing import Optional, List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import PaginationDep
from app.services.public_service import PublicService
from app.schemas import public as schemas

router = APIRouter(prefix="/public", tags=["Public API"])

async def get_public_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> PublicService:
    return PublicService(db, redis)

PublicServiceDep = Annotated[PublicService, Depends(get_public_service)]

# ========== СПЕЦИАЛЬНОСТИ ==========

@router.get("/specialties", response_model=schemas.PaginatedResponse)
async def get_specialties(
    service: PublicServiceDep,
    pagination: PaginationDep
):
    """
    Получить список всех специальностей с пагинацией
    """
    skip, limit = pagination
    items, total = await service.get_specialties(skip, limit)
    
    return {
        "data": items,
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/specialties/{specialty_id}", response_model=schemas.SpecialtyDetail)
async def get_specialty_detail(
    specialty_id: Annotated[int, Path(..., description="ID специальности")],
    service: PublicServiceDep
):
    """
    Получить детальную информацию о специальности по ID
    """
    specialty = await service.get_specialty_detail(specialty_id)
    if not specialty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specialty not found"
        )
    return specialty

# ========== ТЕСТИРОВАНИЕ ==========

@router.get("/test/questions", response_model=List[schemas.TestQuestionPublic])
async def get_test_questions(
    service: PublicServiceDep
):
    """
    Получить все вопросы профориентационного теста
    """
    return await service.get_test_questions()

@router.post("/test/submit", response_model=schemas.TestResultPublic)
async def submit_test(
    answers: schemas.TestSubmit,
    service: PublicServiceDep
):
    """
    Отправить ответы на тест и получить результат
    """
    return await service.calculate_test_result(answers.answers)

# ========== ДОКУМЕНТЫ ==========

@router.get("/documents", response_model=List[schemas.DocumentPublic])
async def get_documents(
    specialty_id: Annotated[Optional[int], Query(description="Фильтр по специальности")] = None,
    category: Annotated[Optional[str], Query(description="Категория документов")] = None,
    service: PublicServiceDep
):
    """
    Получить список документов для скачивания
    """
    return await service.get_documents(specialty_id, category)

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: Annotated[int, Path(description="ID документа")],
    service: PublicServiceDep
):
    """
    Скачать документ (редирект на URL файла)
    """
    # Получаем документ из БД
    documents = await service.get_documents()
    document = next((d for d in documents if d.id == document_id), None)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Увеличиваем счетчик скачиваний
    await service.increment_download_count(document_id)
    
    # Редирект на URL файла
    return RedirectResponse(url=str(document.file_url))

# ========== FAQ ==========

@router.get("/faqs", response_model=List[schemas.FAQPublic])
async def get_faqs(
    category: Annotated[Optional[str], Query(description="Категория вопросов")] = None,
    service: PublicServiceDep
):
    """
    Получить список часто задаваемых вопросов
    """
    return await service.get_faqs(category)

# ========== НОВОСТИ ==========

@router.get("/news", response_model=schemas.PaginatedResponse)
async def get_news(
    service: PublicServiceDep,
    pagination: PaginationDep
):
    """
    Получить список новостей с пагинацией
    """
    skip, limit = pagination
    items, total = await service.get_news(skip, limit)
    
    return {
        "data": items,
        "total": total,
        "limit": limit,
        "offset": skip
    }

@router.get("/news/{news_id}", response_model=schemas.NewsDetail)
async def get_news_detail(
    news_id: Annotated[int, Path(description="ID новости")],
    service: PublicServiceDep
):
    """
    Получить детальную информацию о новости
    """
    news = await service.get_news_detail(news_id)
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    return news

# ========== ИНФОРМАЦИЯ ==========

@router.get("/about", response_model=schemas.AboutPublic)
async def get_about(
    service: PublicServiceDep
):
    """
    Получить информацию о колледже
    """
    about = await service.get_about()
    if not about:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="About information not found"
        )
    return about

@router.get("/admission", response_model=schemas.AdmissionYear)
async def get_admission_info(
    year: Annotated[Optional[int], Query(description="Год набора")] = None,
    service: PublicServiceDep
):
    """
    Получить информацию о приеме (таблица мест)
    """
    admission = await service.get_admission_info(year)
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission information not found"
        )
    return admission