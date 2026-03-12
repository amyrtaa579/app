from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse

from app.core.database import get_redis
from app.api.v1.dependencies import CurrentAdminDep
from app.services.parse_service import ParseTaskService

router = APIRouter(prefix="/admin/parse", tags=["Admin Parse"])

async def get_parse_service(
    redis: Annotated[AsyncSession, Depends(get_redis)]
) -> ParseTaskService:
    return ParseTaskService(redis)

ParseServiceDep = Annotated[ParseTaskService, Depends(get_parse_service)]

@router.post("/news", response_model=dict)
async def start_news_parse(
    max_news: Annotated[int, Query(ge=1, le=50, description="Максимум новостей")] = 10,
    days_back: Annotated[int, Query(ge=1, le=90, description="За сколько дней")] = 30,
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Запустить парсинг новостей с официального сайта
    """
    task = await service.create_parse_task(max_news, days_back)
    
    return {
        "message": "Parse task started",
        "task_id": task["task_id"],
        "status": task["status"],
        "created_at": task["created_at"]
    }

@router.get("/news/status/{task_id}", response_model=dict)
async def get_parse_status(
    task_id: Annotated[str, Path(description="ID задачи")],
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Получить статус задачи парсинга
    """
    task = await service.get_task_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task

@router.get("/news/tasks", response_model=List[dict])
async def get_parse_tasks(
    limit: Annotated[int, Query(le=100, description="Количество задач")] = 50,
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Получить список всех задач парсинга
    """
    tasks = await service.get_all_tasks(limit)
    return tasks

@router.delete("/news/tasks/{task_id}", response_model=dict)
async def cancel_parse_task(
    task_id: Annotated[str, Path(description="ID задачи")],
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Отменить выполняющуюся задачу
    """
    cancelled = await service.cancel_task(task_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be cancelled or not found"
        )
    
    return {"message": "Task cancelled", "task_id": task_id}

@router.get("/news/last", response_model=Optional[dict])
async def get_last_parse(
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Получить результат последнего парсинга
    """
    return await service.get_last_parse_result()

@router.post("/news/cleanup", response_model=dict)
async def cleanup_old_tasks(
    days: Annotated[int, Query(description="Старше скольких дней")] = 7,
    service: ParseServiceDep,
    current_admin: CurrentAdminDep
):
    """
    Очистить старые задачи парсинга
    """
    await service.cleanup_old_tasks(days)
    return {"message": f"Tasks older than {days} days cleaned up"}