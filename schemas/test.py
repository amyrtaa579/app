from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class TestSessionStart(BaseModel):
    """Запрос на начало теста"""
    user_id: str = Field(..., description="ID пользователя в Telegram")

class TestSessionResponse(BaseModel):
    """Ответ с данными сессии"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime

class TestAnswerRequest(BaseModel):
    """Запрос на сохранение ответа"""
    session_id: str
    question_id: int
    option_ids: List[int] = Field(..., min_items=1)

class TestProgressResponse(BaseModel):
    """Прогресс прохождения теста"""
    session_id: str
    current_question: int
    total_questions: int
    progress_percent: float
    completed: bool
    has_result: bool
    next_question: Optional[Dict] = None

class TestResultDetail(BaseModel):
    """Детальный результат теста"""
    specialty_id: Optional[int]
    specialty_name: str
    title: str
    description: str
    strengths: List[str]
    image_url: Optional[str] = None
    total_points: int
    question_points: Dict[int, int]
    timestamp: datetime

class TestStatistics(BaseModel):
    """Статистика тестирования"""
    total_tests_today: int
    total_tests_this_week: int
    average_score: Optional[float] = None
    most_popular_specialty: Optional[str] = None
    completion_rate: Optional[float] = None