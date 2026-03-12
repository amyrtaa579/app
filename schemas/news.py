from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import date, datetime

class NewsImageBase(BaseModel):
    image_url: HttpUrl
    caption: Optional[str] = None
    sort_order: Optional[int] = 0

class NewsImageCreate(NewsImageBase):
    pass

class NewsImage(NewsImageBase):
    id: int
    news_id: int
    created_at: datetime

class NewsBase(BaseModel):
    title: str
    date: date
    content_html: str
    preview_text: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    is_published: bool = True

class NewsCreate(NewsBase):
    images: List[NewsImageCreate] = [] # <-- Список картинок для этой новости

class News(NewsBase):
    id: int
    views_count: int
    created_at: datetime
    updated_at: datetime
    images: List[NewsImage] = [] # <-- Картинки в ответе

    class Config:
        from_attributes = True