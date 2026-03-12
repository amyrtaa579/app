from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

# ========== БАЗОВЫЕ СХЕМЫ ==========

class AdminBase(BaseModel):
    login: str
    full_name: Optional[str] = None

class AdminCreate(AdminBase):
    password: str

class AdminUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

class Admin(AdminBase):
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SuccessResponse(BaseModel):
    message: str
    id: Optional[int] = None

class ErrorResponse(BaseModel):
    detail: str

# ========== СПЕЦИАЛЬНОСТИ ==========

class RealityAdmin(BaseModel):
    id: Optional[int] = None
    type: str  # 'plus', 'minus', 'work_place', 'duties'
    content: str
    sort_order: int = 0

class FactAdmin(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    image_url: Optional[HttpUrl] = None
    sort_order: int = 0

class SpecialtyAdminCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    education_requirements: Optional[str] = None
    duration: Optional[str] = None
    budget_places: int = 0
    paid_places: int = 0
    image_url: Optional[HttpUrl] = None
    realities: List[RealityAdmin] = []
    facts: List[FactAdmin] = []

class SpecialtyAdminUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    education_requirements: Optional[str] = None
    duration: Optional[str] = None
    budget_places: Optional[int] = None
    paid_places: Optional[int] = None
    image_url: Optional[HttpUrl] = None
    realities: Optional[List[RealityAdmin]] = None
    facts: Optional[List[FactAdmin]] = None

class SpecialtyAdmin(SpecialtyAdminCreate):
    id: int
    total_places: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ========== ТЕСТЫ ==========

class TestOptionAdmin(BaseModel):
    id: Optional[int] = None
    text: str
    image_url: Optional[HttpUrl] = None
    points: int = 0
    sort_order: int = 0

class TestQuestionAdminCreate(BaseModel):
    text: str
    image_url: Optional[HttpUrl] = None
    type: str = "single"
    sort_order: int = 0
    is_active: bool = True
    options: List[TestOptionAdmin]

class TestQuestionAdminUpdate(BaseModel):
    text: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    type: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    options: Optional[List[TestOptionAdmin]] = None

class TestQuestionAdmin(TestQuestionAdminCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TestResultAdminCreate(BaseModel):
    specialty_id: Optional[int] = None
    min_score: int
    max_score: int
    title: str
    description: str
    strengths: List[str] = []
    image_url: Optional[HttpUrl] = None

class TestResultAdminUpdate(BaseModel):
    specialty_id: Optional[int] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    strengths: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None

class TestResultAdmin(TestResultAdminCreate):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ========== ДОКУМЕНТЫ ==========

class DocumentAdminCreate(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: HttpUrl
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_active: bool = True
    specialty_ids: List[int] = []

class DocumentAdminUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None
    specialty_ids: Optional[List[int]] = None

class DocumentAdmin(DocumentAdminCreate):
    id: int
    download_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ========== FAQ ==========

class FAQAdminCreate(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    document_id: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True

class FAQAdminUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    document_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class FAQAdmin(FAQAdminCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ========== НОВОСТИ ==========

class NewsImageAdmin(BaseModel):
    id: Optional[int] = None
    image_url: HttpUrl
    caption: Optional[str] = None
    sort_order: int = 0

class NewsAdminCreate(BaseModel):
    title: str
    date: datetime
    content_html: str
    preview_text: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    is_published: bool = True
    images: List[NewsImageAdmin] = []

class NewsAdminUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    content_html: Optional[str] = None
    preview_text: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    is_published: Optional[bool] = None
    images: Optional[List[NewsImageAdmin]] = None

class NewsAdmin(NewsAdminCreate):
    id: int
    views_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ========== ИНФОРМАЦИЯ ==========

class AboutAdminUpdate(BaseModel):
    content: str

class AboutAdmin(AboutAdminUpdate):
    updated_at: datetime
    updated_by: int
    
    model_config = ConfigDict(from_attributes=True)

class AdmissionInfoAdminCreate(BaseModel):
    year: int
    data: List[dict]
    is_current: bool = True

class AdmissionInfoAdminUpdate(BaseModel):
    data: Optional[List[dict]] = None
    is_current: Optional[bool] = None

class AdmissionInfoAdmin(AdmissionInfoAdminCreate):
    id: int
    updated_at: datetime
    updated_by: int
    
    model_config = ConfigDict(from_attributes=True)