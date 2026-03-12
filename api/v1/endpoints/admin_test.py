from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.api.v1.dependencies import CurrentAdminDep
from app.services.admin_test import TestQuestionAdminService, TestResultAdminService
from app.schemas import admin as schemas

router = APIRouter(prefix="/admin/test", tags=["Admin Test"])

# ========== ВОПРОСЫ ТЕСТА ==========

@router.get("/questions", response_model=List[schemas.TestQuestionAdmin])
async def get_test_questions(
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить все вопросы теста"""
    service = TestQuestionAdminService(db, redis)
    items, _ = await service.get_multi(limit=1000)
    return items

@router.get("/questions/{question_id}", response_model=schemas.TestQuestionAdmin)
async def get_test_question(
    question_id: Annotated[int, Path(description="ID вопроса")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить вопрос с вариантами ответов"""
    service = TestQuestionAdminService(db, redis)
    question = await service.get_with_options(question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question

@router.post("/questions", response_model=schemas.TestQuestionAdmin, status_code=status.HTTP_201_CREATED)
async def create_test_question(
    question_data: schemas.TestQuestionAdminCreate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Создать новый вопрос теста"""
    service = TestQuestionAdminService(db, redis)
    return await service.create_with_options(question_data)

@router.put("/questions/{question_id}", response_model=schemas.TestQuestionAdmin)
async def update_test_question(
    question_id: Annotated[int, Path(description="ID вопроса")],
    question_data: schemas.TestQuestionAdminUpdate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Обновить вопрос теста"""
    service = TestQuestionAdminService(db, redis)
    question = await service.update_with_options(question_id, question_data)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question

@router.delete("/questions/{question_id}", response_model=schemas.SuccessResponse)
async def delete_test_question(
    question_id: Annotated[int, Path(description="ID вопроса")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Удалить вопрос теста"""
    service = TestQuestionAdminService(db, redis)
    success = await service.delete(question_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return {"message": "Question deleted successfully", "id": question_id}

# ========== РЕЗУЛЬТАТЫ ТЕСТА ==========

@router.get("/results", response_model=List[schemas.TestResultAdmin])
async def get_test_results(
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить все результаты теста"""
    service = TestResultAdminService(db, redis)
    items, _ = await service.get_multi(limit=1000)
    return items

@router.get("/results/{result_id}", response_model=schemas.TestResultAdmin)
async def get_test_result(
    result_id: Annotated[int, Path(description="ID результата")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Получить результат теста"""
    service = TestResultAdminService(db, redis)
    result = await service.get_with_specialty(result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return result

@router.post("/results", response_model=schemas.TestResultAdmin, status_code=status.HTTP_201_CREATED)
async def create_test_result(
    result_data: schemas.TestResultAdminCreate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Создать новый результат теста"""
    service = TestResultAdminService(db, redis)
    return await service.create(**result_data.model_dump())

@router.put("/results/{result_id}", response_model=schemas.TestResultAdmin)
async def update_test_result(
    result_id: Annotated[int, Path(description="ID результата")],
    result_data: schemas.TestResultAdminUpdate,
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Обновить результат теста"""
    service = TestResultAdminService(db, redis)
    result = await service.update(result_id, result_data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return result

@router.delete("/results/{result_id}", response_model=schemas.SuccessResponse)
async def delete_test_result(
    result_id: Annotated[int, Path(description="ID результата")],
    current_admin: CurrentAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
):
    """Удалить результат теста"""
    service = TestResultAdminService(db, redis)
    success = await service.delete(result_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return {"message": "Result deleted successfully", "id": result_id}