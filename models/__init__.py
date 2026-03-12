from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Table
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# Таблица для связи документов со специальностями (many-to-many)
document_specialty = Table(
    'document_specialty',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
    Column('specialty_id', Integer, ForeignKey('specialties.id', ondelete='CASCADE'), primary_key=True)
)

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    login = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Specialty(Base):
    __tablename__ = 'specialties'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    education_requirements = Column(String(255))
    duration = Column(String(50))
    budget_places = Column(Integer, default=0)
    paid_places = Column(Integer, default=0)
    image_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связи
    realities = relationship("Reality", back_populates="specialty", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="specialty", cascade="all, delete-orphan")
    documents = relationship("Document", secondary=document_specialty, back_populates="specialties")
    
    @property
    def total_places(self):
        return self.budget_places + self.paid_places

class Reality(Base):
    __tablename__ = 'realities'
    
    id = Column(Integer, primary_key=True)
    specialty_id = Column(Integer, ForeignKey('specialties.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(50), nullable=False)  # 'plus', 'minus', 'work_place', 'duties'
    content = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    specialty = relationship("Specialty", back_populates="realities")

class Fact(Base):
    __tablename__ = 'facts'
    
    id = Column(Integer, primary_key=True)
    specialty_id = Column(Integer, ForeignKey('specialties.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    specialty = relationship("Specialty", back_populates="facts")

class TestQuestion(Base):
    __tablename__ = 'test_questions'
    
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    image_url = Column(String(500))
    type = Column(String(20), nullable=False, default='single')  # 'single' or 'multiple'
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    options = relationship("TestOption", back_populates="question", cascade="all, delete-orphan")

class TestOption(Base):
    __tablename__ = 'test_options'
    
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('test_questions.id', ondelete='CASCADE'), nullable=False)
    text = Column(String(500), nullable=False)
    image_url = Column(String(500))
    points = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    question = relationship("TestQuestion", back_populates="options")

class TestResult(Base):
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True)
    specialty_id = Column(Integer, ForeignKey('specialties.id', ondelete='SET NULL'))
    min_score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    strengths = Column(Text)  # JSON массив или текст
    image_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    specialty = relationship("Specialty")

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    download_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    specialties = relationship("Specialty", secondary=document_specialty, back_populates="documents")

class FAQ(Base):
    __tablename__ = 'faqs'
    
    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100))
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='SET NULL'))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    document = relationship("Document")

class About(Base):
    __tablename__ = 'about'
    
    id = Column(Integer, primary_key=True, default=1)  # Только одна запись
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, ForeignKey('admins.id'))
    
    admin = relationship("Admin")

class AdmissionInfo(Base):
    __tablename__ = 'admission_info'
    
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # JSONB в PostgreSQL
    is_current = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, ForeignKey('admins.id'))
    
    admin = relationship("Admin")

class News(Base):
    __tablename__ = 'news'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    content_html = Column(Text, nullable=False)
    preview_text = Column(String(500))
    source_url = Column(String(500))
    is_published = Column(Boolean, default=True)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    images = relationship("NewsImage", back_populates="news", cascade="all, delete-orphan")

class NewsImage(Base):
    __tablename__ = 'news_images'
    
    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey('news.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String(500), nullable=False)
    caption = Column(String(255))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    news = relationship("News", back_populates="images")