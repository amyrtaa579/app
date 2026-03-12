from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.v1.dependencies import CurrentAdminDep
from app.services.statistics import StatisticsService
from app.schemas import statistics as schemas

router = APIRouter(prefix="/admin/stats", tags=["Admin Statistics"])

async def get_stats_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> StatisticsService:
    return StatisticsService(db)

StatsServiceDep = Annotated[StatisticsService, Depends(get_stats_service)]

@router.get("/dashboard", response_model=schemas.DashboardResponse)
async def get_dashboard(
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить данные для главной панели статистики"""
    
    # Статистика за сегодня
    today = datetime.utcnow().date()
    daily_stats = await service.get_daily_stats(1)
    
    today_data = daily_stats[0] if daily_stats else {
        "users": 0, "views": 0, "downloads": 0, "tests": 0
    }
    
    # Популярный контент
    popular = await service.get_popular_content(limit=5)
    
    # Последние действия
    recent = await service.get_admin_activity(days=1)
    
    # Ежедневная статистика для графика
    chart_data = await service.get_daily_stats(7)
    
    return {
        "total_users_today": today_data["users"],
        "total_views_today": today_data["views"],
        "total_downloads_today": today_data["downloads"],
        "total_tests_today": today_data["tests"],
        "popular_specialties": popular["popular_specialties"],
        "popular_documents": popular["popular_documents"],
        "recent_activity": recent[:10],
        "daily_chart": chart_data
    }

@router.get("/specialties/{specialty_id}", response_model=schemas.SpecialtyStatResponse)
async def get_specialty_stats(
    specialty_id: Annotated[int, Path(description="ID специальности")],
    period: Annotated[str, Query(description="Период (7d, 30d, all)")] = "30d",
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить статистику по специальности"""
    stats = await service.get_specialty_stats(specialty_id, period)
    return stats

@router.get("/documents/{document_id}", response_model=schemas.DocumentStatResponse)
async def get_document_stats(
    document_id: Annotated[int, Path(description="ID документа")],
    period: Annotated[str, Query(description="Период (7d, 30d, all)")] = "30d",
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить статистику по документу"""
    stats = await service.get_document_stats(document_id, period)
    return stats

@router.get("/tests", response_model=schemas.TestStatResponse)
async def get_test_stats(
    period: Annotated[str, Query(description="Период (7d, 30d, all)")] = "30d",
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить статистику по тестам"""
    stats = await service.get_test_stats(period)
    return stats

@router.get("/popular", response_model=schemas.PopularContentResponse)
async def get_popular_content(
    limit: Annotated[int, Query(le=20, description="Количество элементов")] = 10,
    period: Annotated[str, Query(description="Период (7d, 30d, all)")] = "30d",
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить популярный контент"""
    popular = await service.get_popular_content(limit, period)
    return popular

@router.get("/daily", response_model=List[schemas.DailyStatResponse])
async def get_daily_stats(
    days: Annotated[int, Query(le=90, description="Количество дней")] = 30,
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить ежедневную статистику"""
    stats = await service.get_daily_stats(days)
    return stats

@router.get("/admin-activity", response_model=List[schemas.AdminLogResponse])
async def get_admin_activity(
    days: Annotated[int, Query(le=90, description="За сколько дней")] = 7,
    admin_id: Annotated[Optional[int], Query(description="ID администратора")] = None,
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Получить активность администраторов"""
    logs = await service.get_admin_activity(days, admin_id)
    return logs

@router.post("/aggregate", response_model=dict)
async def aggregate_stats(
    date: Annotated[Optional[str], Query(description="Дата в формате YYYY-MM-DD")] = None,
    service: StatsServiceDep,
    current_admin: CurrentAdminDep
):
    """Запустить агрегацию статистики за день"""
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.utcnow().date()
    
    await service.aggregate_daily_stats(target_date)
    
    return {"message": f"Statistics aggregated for {target_date}"}