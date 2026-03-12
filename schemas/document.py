from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: HttpUrl  # <-- Ссылка на файл после загрузки
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_active: bool = True

class DocumentCreate(DocumentBase):
    specialty_ids: List[int] = []  # ID специальностей, к которым привязан документ

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None
    specialty_ids: Optional[List[int]] = None

class Document(DocumentBase):
    id: int
    download_count: int
    created_at: datetime
    updated_at: datetime
    specialties: List["SpecialtyBase"] = []  # Базовая информация о специальностях

    class Config:
        from_attributes = True

class SpecialtyBase(BaseModel):
    id: int
    code: str
    name: str
    
    class Config:
        from_attributes = True