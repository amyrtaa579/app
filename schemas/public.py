from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime, date

# ========== СПЕЦИАЛЬНОСТИ ==========

class RealityPublic(BaseModel):
    """Реалии профессии для публичного API"""
    type: str  # 'plus', 'minus', 'work_place', 'duties'
    content: str

class FactPublic(BaseModel):
    """Интересный факт для публичного API"""
    title: str
    description: str
    image_url: Optional[HttpUrl] = None

class SpecialtyListItem(BaseModel):
    """Специальность для списка"""
    id: int
    code: str
    name: str
    duration: Optional[str] = None
    budget_places: int
    paid_places: int
    total_places: int = Field(..., alias='total_places')
    image_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class SpecialtyDetail(SpecialtyListItem):
    """Детальная информация о специальности"""
    description: Optional[str] = None
    education_requirements: Optional[str] = None
    realities: List[RealityPublic] = []
    facts: List[FactPublic] = []

# ========== ТЕСТИРОВАНИЕ ==========

class TestOptionPublic(BaseModel):
    """Вариант ответа на вопрос теста"""
    id: int
    text: str
    image_url: Optional[HttpUrl] = None

class TestQuestionPublic(BaseModel):
    """Вопрос теста для прохождения"""
    id: int
    text: str
    image_url: Optional[HttpUrl] = None
    type: str  # 'single' or 'multiple'
    options: List[TestOptionPublic]

class TestAnswer(BaseModel):
    """Ответ пользователя на один вопрос"""
    question_id: int
    option_ids: List[int]  # Массив ID выбранных вариантов

class TestSubmit(BaseModel):
    """Отправка результатов теста"""
    answers: List[TestAnswer]

class TestResultPublic(BaseModel):
    """Результат тестирования"""
    specialty_id: int
    specialty_name: str
    title: str
    description: str
    strengths: List[str]  # Сильные стороны как список
    image_url: Optional[HttpUrl] = None

# ========== ДОКУМЕНТЫ ==========

class DocumentPublic(BaseModel):
    """Документ для скачивания"""
    id: int
    title: str
    description: Optional[str] = None
    file_url: HttpUrl
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

class DocumentCategory(BaseModel):
    """Категория документов"""
    category: str  # '9_class', '11_class', 'parents'
    name: str  # Человекочитаемое название
    documents: List[DocumentPublic]

# ========== FAQ ==========

class FAQPublic(BaseModel):
    """Часто задаваемый вопрос"""
    id: int
    question: str
    answer: str
    category: Optional[str] = None

# ========== НОВОСТИ ==========

class NewsImagePublic(BaseModel):
    """Изображение новости"""
    image_url: HttpUrl
    caption: Optional[str] = None

class NewsListItem(BaseModel):
    """Новость в списке"""
    id: int
    title: str
    date: datetime
    preview_text: Optional[str] = None
    image_url: Optional[HttpUrl] = None  # Первое изображение для превью

class NewsDetail(NewsListItem):
    """Детальная новость"""
    content_html: str
    images: List[NewsImagePublic] = []
    source_url: Optional[HttpUrl] = None

# ========== ИНФОРМАЦИЯ ==========

class AboutPublic(BaseModel):
    """Информация о колледже"""
    content: str
    updated_at: datetime

class AdmissionYear(BaseModel):
    """Информация о приеме за год"""
    year: int
    data: List[dict]  # Таблица приема

class PaginatedResponse(BaseModel):
    """Ответ с пагинацией"""
    data: List
    total: int
    limit: int
    offset: int