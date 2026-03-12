from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from app.models import TestQuestion, TestOption, TestResult, Specialty
from app.schemas import admin as schemas
from app.services.base_crud import BaseCRUDService

class TestQuestionAdminService(BaseCRUDService[
    TestQuestion,
    schemas.TestQuestionAdminCreate,
    schemas.TestQuestionAdminUpdate
]):
    """Сервис для управления вопросами теста"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=TestQuestion,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:test:question",
            cache_ttl=1800
        )
    
    async def create_with_options(
        self,
        schema: schemas.TestQuestionAdminCreate
    ) -> TestQuestion:
        """Создание вопроса с вариантами ответов"""
        
        # Создаем вопрос
        question_data = schema.model_dump(exclude={"options"})
        question = TestQuestion(**question_data)
        self.db.add(question)
        await self.db.flush()
        
        # Добавляем варианты
        for option_data in schema.options:
            option = TestOption(
                question_id=question.id,
                **option_data.model_dump()
            )
            self.db.add(option)
        
        await self.db.commit()
        await self.db.refresh(question)
        
        # Инвалидируем кэш
        await self._invalidate_cache()
        # Также инвалидируем публичный кэш теста
        await self.redis.delete("test:questions")
        
        return question
    
    async def get_with_options(self, id: int) -> Optional[TestQuestion]:
        """Получение вопроса с вариантами"""
        result = await self.db.execute(
            select(TestQuestion)
            .where(TestQuestion.id == id)
            .options(selectinload(TestQuestion.options))
        )
        question = result.scalar_one_or_none()
        
        if question:
            question.options.sort(key=lambda x: x.sort_order)
        
        return question
    
    async def update_with_options(
        self,
        id: int,
        schema: schemas.TestQuestionAdminUpdate
    ) -> Optional[TestQuestion]:
        """Обновление вопроса с вариантами"""
        
        question = await self.get_with_options(id)
        if not question:
            return None
        
        # Обновляем основные поля
        update_data = schema.model_dump(exclude={"options"}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(question, field, value)
        
        # Обновляем варианты
        if schema.options is not None:
            # Удаляем старые
            for option in question.options:
                await self.db.delete(option)
            
            # Добавляем новые
            for option_data in schema.options:
                option = TestOption(
                    question_id=question.id,
                    **option_data.model_dump()
                )
                self.db.add(option)
        
        await self.db.commit()
        await self.db.refresh(question)
        
        # Инвалидируем кэш
        await self._invalidate_cache(id)
        await self._invalidate_cache()
        await self.redis.delete("test:questions")
        
        return question

class TestResultAdminService(BaseCRUDService[
    TestResult,
    schemas.TestResultAdminCreate,
    schemas.TestResultAdminUpdate
]):
    """Сервис для управления результатами теста"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        super().__init__(
            model=TestResult,
            db=db,
            redis=redis_client,
            cache_key_prefix="admin:test:result",
            cache_ttl=1800
        )
    
    async def get_with_specialty(self, id: int) -> Optional[TestResult]:
        """Получение результата со специальностью"""
        result = await self.db.execute(
            select(TestResult)
            .where(TestResult.id == id)
            .options(selectinload(TestResult.specialty))
        )
        return result.scalar_one_or_none()
    
    async def get_by_score(self, score: int) -> Optional[TestResult]:
        """Получение результата по сумме баллов"""
        result = await self.db.execute(
            select(TestResult)
            .where(
                TestResult.min_score <= score,
                TestResult.max_score >= score
            )
            .options(selectinload(TestResult.specialty))
        )
        return result.scalar_one_or_none()