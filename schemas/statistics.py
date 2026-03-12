from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DateRange(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SpecialtyStatResponse(BaseModel):
    specialty_id: int
    total_views: int
    unique_users: int
    period_views: int
    last_viewed: Optional[datetime] = None

class DocumentStatResponse(BaseModel):
    document_id: int
    total_downloads: int
    unique_users: int
    period_downloads: int
    last_downloaded: Optional[datetime] = None

class TestStatResponse(BaseModel):
    total_tests: int
    period_tests: int
    average_score: float
    popular_results: List[Dict[str, Any]]
    unique_users: int

class DailyStatResponse(BaseModel):
    date: str
    users: int
    views: int
    downloads: int
    tests: int

class PopularContentResponse(BaseModel):
    popular_specialties: List[Dict[str, Any]]
    popular_documents: List[Dict[str, Any]]
    popular_test_results: List[Dict[str, Any]]

class AdminLogResponse(BaseModel):
    id: int
    admin: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    changes: Optional[Dict] = None
    ip_address: Optional[str] = None
    created_at: str

class DashboardResponse(BaseModel):
    """Главная панель статистики"""
    total_users_today: int
    total_views_today: int
    total_downloads_today: int
    total_tests_today: int
    popular_specialties: List[Dict[str, Any]]
    popular_documents: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    daily_chart: List[DailyStatResponse]