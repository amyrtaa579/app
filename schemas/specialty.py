from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

# Базовая схема для Reality (реалии профессии)
class RealityBase(BaseModel):
    type: str  # 'plus', 'minus', 'work_place', 'duties'
    content: str
    sort_order: Optional[int] = 0

class RealityCreate(RealityBase):
    pass

class Reality(RealityBase):
    id: int
    specialty_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Базовая схема для Fact (интересные факты)
class FactBase(BaseModel):
    title: str
    description: str
    image_url: Optional[HttpUrl] = None  # <--- Ссылка на картинку
    sort_order: Optional[int] = 0

class FactCreate(FactBase):
    pass

class Fact(FactBase):
    id: int
    specialty_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схема для специальности (ответ API)
class Specialty(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    education_requirements: Optional[str] = None
    duration: Optional[str] = None
    budget_places: int = 0
    paid_places: int = 0
    total_places: int = Field(..., alias='total_places') # computed field
    image_url: Optional[HttpUrl] = None  # <--- Ссылка на главное фото
    realities: List[Reality] = []
    facts: List[Fact] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# Схема для создания/обновления специальности (админка)
class SpecialtyCreateUpdate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    education_requirements: Optional[str] = None
    duration: Optional[str] = None
    budget_places: Optional[int] = 0
    paid_places: Optional[int] = 0
    image_url: Optional[HttpUrl] = None  # <--- Ссылка на главное фото. Админ ее получит после загрузки файла.