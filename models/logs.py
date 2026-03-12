from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

class AdminLog(Base):
    """Логи действий администраторов"""
    __tablename__ = 'admin_logs'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = Column(String(50), nullable=False)  # specialty, news, document, etc.
    entity_id = Column(Integer, nullable=True)
    changes = Column(JSON)  # Что изменилось (старое/новое значение)
    ip_address = Column(String(45))  # IPv6 поддерживает до 45 символов
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    admin = relationship("Admin")

class UserActionLog(Base):
    """Логи действий пользователей (абитуриентов)"""
    __tablename__ = 'user_action_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)  # Telegram ID
    action = Column(String(50), nullable=False)  # view_specialty, download_document, start_test, etc.
    entity_type = Column(String(50))  # specialty, document, news, etc.
    entity_id = Column(Integer)
    metadata = Column(JSON)  # Дополнительные данные
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class SpecialtyStat(Base):
    """Статистика просмотров специальностей"""
    __tablename__ = 'specialty_stats'
    
    id = Column(Integer, primary_key=True)
    specialty_id = Column(Integer, ForeignKey('specialties.id', ondelete='CASCADE'), nullable=False)
    views_count = Column(Integer, default=0)
    unique_users = Column(JSON, default=list)  # Храним ID пользователей для подсчета уникальных
    last_viewed_at = Column(DateTime)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    specialty = relationship("Specialty")

class DocumentDownloadStat(Base):
    """Статистика скачиваний документов"""
    __tablename__ = 'document_download_stats'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    download_count = Column(Integer, default=0)
    unique_users = Column(JSON, default=list)
    last_downloaded_at = Column(DateTime)
    downloaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    document = relationship("Document")

class TestStat(Base):
    """Статистика прохождения тестов"""
    __tablename__ = 'test_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    result_id = Column(Integer, ForeignKey('test_results.id', ondelete='SET NULL'))
    score = Column(Integer)
    answers = Column(JSON)  # Сохраняем ответы для анализа
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    time_spent = Column(Integer)  # Время в секундах
    
    result = relationship("TestResult")

class DailyStat(Base):
    """Ежедневная статистика"""
    __tablename__ = 'daily_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    total_users = Column(Integer, default=0)  # Уникальные пользователи за день
    total_views = Column(Integer, default=0)  # Всего просмотров
    total_downloads = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    popular_specialties = Column(JSON, default=list)  # Топ-5 специальностей
    popular_documents = Column(JSON, default=list)  # Топ-5 документов
    created_at = Column(DateTime, default=datetime.utcnow)