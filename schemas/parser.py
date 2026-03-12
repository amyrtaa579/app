from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class ParsedNewsImage(BaseModel):
    """Изображение из новости"""
    url: str
    caption: Optional[str] = None
    is_main: bool = False

class ParsedNews(BaseModel):
    """Распарсенная новость"""
    title: str
    date: datetime
    content_html: str
    preview_text: Optional[str] = None
    source_url: str
    images: List[ParsedNewsImage] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ParseTask(BaseModel):
    """Задача на парсинг"""
    task_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    news_count: int = 0
    error: Optional[str] = None
    result: Optional[List[ParsedNews]] = None