from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.services.test_service import TestService
from app.schemas import public as schemas
from app.schemas import test as test_schemas

router = APIRouter(prefix="/test", tags=["Testing"])

async def get_test_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> TestService:
    return TestService(db, redis)

TestServiceDep = Annotated[TestService, Depends(get_test_service)]

@router.post("/start", response_model=test_schemas.TestSessionResponse)
async def start_test(
    user_data: test_schemas.TestSessionStart,
    service: TestServiceDep
):
    """
    Начать новый тест.
    Возвращает ID сессии для последующих запросов.
    """
    session_id = await service.start_test(user_data.user_id)
    
    # Получаем данные сессии
    session = await service.session_service.get_session(session_id)
    
    return {
        "session_id": session_id,
        "user_id": session["user_id"],
        "created_at": datetime.fromisoformat(session["created_at"]),
        "expires_at": datetime.fromisoformat(session["created_at"]) + timedelta(hours=1)
    }

@router.get("/questions", response_model=List[schemas.TestQuestionPublic])
async def get_questions(
    service: TestServiceDep
):
    """
    Получить все вопросы теста.
    """
    questions = await service.get_questions()
    return questions

@router.post("/answer", response_model=test_schemas.TestProgressResponse)
async def save_answer(
    answer_data: test_schemas.TestAnswerRequest,
    service: TestServiceDep
):
    """
    Сохранить ответ на вопрос.
    """
    success = await service.save_answer(
        answer_data.session_id,
        answer_data.question_id,
        answer_data.option_ids
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session or question already answered"
        )
    
    # Получаем прогресс
    progress = await service.get_test_progress(answer_data.session_id)
    
    # Если это последний вопрос, автоматически завершаем тест
    if progress["current_question"] == progress["total_questions"]:
        result = await service.finish_test(answer_data.session_id)
        progress["result"] = result
    
    return progress

@router.get("/progress/{session_id}", response_model=test_schemas.TestProgressResponse)
async def get_progress(
    session_id: str,
    service: TestServiceDep
):
    """
    Получить прогресс прохождения теста.
    """
    progress = await service.get_test_progress(session_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return progress

@router.post("/finish/{session_id}", response_model=test_schemas.TestResultDetail)
async def finish_test(
    session_id: str,
    service: TestServiceDep
):
    """
    Завершить тест и получить результат.
    """
    result = await service.finish_test(session_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot finish test"
        )
    
    # Увеличиваем счетчик прохождений
    await service.increment_test_counter()
    
    return result

@router.get("/result/{session_id}", response_model=test_schemas.TestResultDetail)
async def get_test_result(
    session_id: str,
    service: TestServiceDep
):
    """
    Получить результат завершенного теста.
    """
    session = await service.session_service.get_session(session_id)
    if not session or not session.get("result"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    return session["result"]

@router.get("/history/{user_id}", response_model=List[test_schemas.TestResultDetail])
async def get_user_history(
    user_id: str,
    limit: Annotated[int, Query(le=50, description="Количество результатов")] = 10,
    service: TestServiceDep
):
    """
    Получить историю тестирований пользователя.
    """
    sessions = await service.session_service.get_user_sessions(user_id)
    
    # Фильтруем только завершенные и сортируем по дате
    completed = [
        s for s in sessions
        if s.get("completed") and s.get("result")
    ]
    completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    
    # Ограничиваем количество
    results = [s["result"] for s in completed[:limit]]
    
    return results

@router.get("/stats", response_model=test_schemas.TestStatistics)
async def get_test_statistics(
    service: TestServiceDep
):
    """
    Получить статистику тестирования (для админки).
    """
    stats = await service.get_test_statistics()
    return stats