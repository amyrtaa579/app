from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
import json

from app.models import (
    Specialty, Reality, Fact, TestQuestion, TestOption, TestResult,
    Document, FAQ, News, NewsImage, About, AdmissionInfo
)
from app.schemas import public as schemas

class PublicService:
    """Сервис для публичных данных (для бота)"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    # ========== СПЕЦИАЛЬНОСТИ ==========
    
    async def get_specialties(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[schemas.SpecialtyListItem], int]:
        """Получить список специальностей с пагинацией"""
        
        # Пробуем получить из кэша
        cache_key = f"specialties:list:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return [schemas.SpecialtyListItem(**item) for item in data["items"]], data["total"]
        
        # Запрос общего количества
        total = await self.db.scalar(select(func.count()).select_from(Specialty))
        
        # Запрос данных
        result = await self.db.execute(
            select(Specialty)
            .order_by(Specialty.code)
            .offset(skip)
            .limit(limit)
        )
        specialties = result.scalars().all()
        
        # Кэшируем результат на 1 час
        items_data = [schemas.SpecialtyListItem.model_validate(s).model_dump() for s in specialties]
        await self.redis.setex(
            cache_key,
            3600,
            json.dumps({"items": items_data, "total": total})
        )
        
        return [schemas.SpecialtyListItem.model_validate(s) for s in specialties], total
    
    async def get_specialty_detail(self, specialty_id: int) -> Optional[schemas.SpecialtyDetail]:
        """Получить детальную информацию о специальности"""
        
        # Пробуем из кэша
        cache_key = f"specialty:{specialty_id}:detail"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return schemas.SpecialtyDetail.model_validate_json(cached)
        
        # Запрос с загрузкой связанных данных
        result = await self.db.execute(
            select(Specialty)
            .where(Specialty.id == specialty_id)
            .options(
                selectinload(Specialty.realities),
                selectinload(Specialty.facts)
            )
        )
        specialty = result.scalar_one_or_none()
        
        if not specialty:
            return None
        
        # Сортируем realities по sort_order
        specialty.realities.sort(key=lambda x: x.sort_order)
        specialty.facts.sort(key=lambda x: x.sort_order)
        
        # Кэшируем на 1 час
        specialty_data = schemas.SpecialtyDetail.model_validate(specialty)
        await self.redis.setex(
            cache_key,
            3600,
            specialty_data.model_dump_json()
        )
        
        return specialty_data
    
    # ========== ТЕСТИРОВАНИЕ ==========
    
    async def get_test_questions(self) -> List[schemas.TestQuestionPublic]:
        """Получить все вопросы теста с вариантами ответов"""
        
        cache_key = "test:questions"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return [schemas.TestQuestionPublic.model_validate_json(q) for q in json.loads(cached)]
        
        # Загружаем вопросы с вариантами
        result = await self.db.execute(
            select(TestQuestion)
            .where(TestQuestion.is_active == True)
            .order_by(TestQuestion.sort_order)
            .options(selectinload(TestQuestion.options))
        )
        questions = result.scalars().all()
        
        # Сортируем варианты
        for q in questions:
            q.options.sort(key=lambda x: x.sort_order)
        
        # Кэшируем на 1 день (тест редко меняется)
        questions_data = [
            schemas.TestQuestionPublic.model_validate(q).model_dump_json()
            for q in questions
        ]
        await self.redis.setex(
            cache_key,
            86400,
            json.dumps(questions_data)
        )
        
        return [schemas.TestQuestionPublic.model_validate(q) for q in questions]
    
    async def calculate_test_result(self, answers: List[schemas.TestAnswer]) -> schemas.TestResultPublic:
        """Рассчитать результат теста по ответам"""
        
        # Суммируем баллы
        total_points = 0
        for answer in answers:
            # Получаем баллы для каждого выбранного варианта
            for option_id in answer.option_ids:
                result = await self.db.execute(
                    select(TestOption.points).where(TestOption.id == option_id)
                )
                points = result.scalar_one_or_none()
                if points:
                    total_points += points
        
        # Находим подходящий результат по диапазону баллов
        result = await self.db.execute(
            select(TestResult)
            .where(
                TestResult.min_score <= total_points,
                TestResult.max_score >= total_points
            )
            .options(selectinload(TestResult.specialty))
        )
        test_result = result.scalar_one_or_none()
        
        if not test_result:
            # Если результат не найден, берем первый (запасной вариант)
            result = await self.db.execute(select(TestResult).limit(1))
            test_result = result.scalar_one()
        
        # Парсим strengths из JSON или текста
        strengths = []
        if test_result.strengths:
            try:
                strengths = json.loads(test_result.strengths)
            except:
                strengths = [test_result.strengths]
        
        return schemas.TestResultPublic(
            specialty_id=test_result.specialty_id,
            specialty_name=test_result.specialty.name if test_result.specialty else "",
            title=test_result.title,
            description=test_result.description,
            strengths=strengths,
            image_url=test_result.image_url
        )
    
    # ========== ДОКУМЕНТЫ ==========
    
    async def get_documents(
        self,
        specialty_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[schemas.DocumentPublic]:
        """Получить список документов с фильтрацией"""
        
        query = select(Document).where(Document.is_active == True)
        
        if specialty_id:
            query = query.join(Document.specialties).where(Specialty.id == specialty_id)
        
        # TODO: добавить фильтр по категории, если нужно
        
        query = query.order_by(Document.title)
        
        result = await self.db.execute(query)
        documents = result.scalars().all()
        
        return [schemas.DocumentPublic.model_validate(d) for d in documents]
    
    async def increment_download_count(self, document_id: int):
        """Увеличить счетчик скачиваний документа"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if document:
            document.download_count += 1
            await self.db.commit()
    
    # ========== FAQ ==========
    
    async def get_faqs(self, category: Optional[str] = None) -> List[schemas.FAQPublic]:
        """Получить список часто задаваемых вопросов"""
        
        cache_key = f"faqs:{category or 'all'}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return [schemas.FAQPublic.model_validate_json(f) for f in json.loads(cached)]
        
        query = select(FAQ).where(FAQ.is_active == True)
        
        if category:
            query = query.where(FAQ.category == category)
        
        query = query.order_by(FAQ.sort_order, FAQ.question)
        
        result = await self.db.execute(query)
        faqs = result.scalars().all()
        
        # Кэшируем на 1 час
        faqs_data = [schemas.FAQPublic.model_validate(f).model_dump_json() for f in faqs]
        await self.redis.setex(
            cache_key,
            3600,
            json.dumps(faqs_data)
        )
        
        return [schemas.FAQPublic.model_validate(f) for f in faqs]
    
    # ========== НОВОСТИ ==========
    
    async def get_news(
        self,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[schemas.NewsListItem], int]:
        """Получить список новостей с пагинацией"""
        
        cache_key = f"news:list:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return [schemas.NewsListItem(**item) for item in data["items"]], data["total"]
        
        # Общее количество
        total = await self.db.scalar(
            select(func.count()).select_from(News).where(News.is_published == True)
        )
        
        # Запрос новостей
        result = await self.db.execute(
            select(News)
            .where(News.is_published == True)
            .order_by(News.date.desc())
            .offset(skip)
            .limit(limit)
        )
        news_list = result.scalars().all()
        
        # Формируем список с первым изображением для превью
        items = []
        for news in news_list:
            # Загружаем первое изображение
            img_result = await self.db.execute(
                select(NewsImage)
                .where(NewsImage.news_id == news.id)
                .order_by(NewsImage.sort_order)
                .limit(1)
            )
            first_image = img_result.scalar_one_or_none()
            
            item = schemas.NewsListItem(
                id=news.id,
                title=news.title,
                date=news.date,
                preview_text=news.preview_text,
                image_url=first_image.image_url if first_image else None
            )
            items.append(item)
        
        # Кэшируем на 15 минут
        items_data = [item.model_dump() for item in items]
        await self.redis.setex(
            cache_key,
            900,
            json.dumps({"items": items_data, "total": total})
        )
        
        return items, total
    
    async def get_news_detail(self, news_id: int) -> Optional[schemas.NewsDetail]:
        """Получить детальную информацию о новости"""
        
        cache_key = f"news:{news_id}:detail"
        cached = await self.redis.get(cache_key)
        
        if cached:
            # Увеличиваем счетчик просмотров асинхронно
            await self.increment_news_views(news_id)
            return schemas.NewsDetail.model_validate_json(cached)
        
        # Запрос новости с изображениями
        result = await self.db.execute(
            select(News)
            .where(News.id == news_id, News.is_published == True)
            .options(selectinload(News.images))
        )
        news = result.scalar_one_or_none()
        
        if not news:
            return None
        
        # Сортируем изображения
        news.images.sort(key=lambda x: x.sort_order)
        
        # Получаем первое изображение для превью
        first_image = news.images[0] if news.images else None
        
        # Создаем объект
        news_detail = schemas.NewsDetail(
            id=news.id,
            title=news.title,
            date=news.date,
            preview_text=news.preview_text,
            content_html=news.content_html,
            source_url=news.source_url,
            image_url=first_image.image_url if first_image else None,
            images=[schemas.NewsImagePublic.model_validate(img) for img in news.images]
        )
        
        # Кэшируем на 1 час
        await self.redis.setex(
            cache_key,
            3600,
            news_detail.model_dump_json()
        )
        
        # Увеличиваем счетчик просмотров
        news.views_count += 1
        await self.db.commit()
        
        return news_detail
    
    async def increment_news_views(self, news_id: int):
        """Увеличить счетчик просмотров новости (асинхронно)"""
        result = await self.db.execute(
            select(News).where(News.id == news_id)
        )
        news = result.scalar_one_or_none()
        if news:
            news.views_count += 1
            await self.db.commit()
    
    # ========== ИНФОРМАЦИЯ ==========
    
    async def get_about(self) -> Optional[schemas.AboutPublic]:
        """Получить информацию о колледже"""
        
        cache_key = "about"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return schemas.AboutPublic.model_validate_json(cached)
        
        result = await self.db.execute(select(About).where(About.id == 1))
        about = result.scalar_one_or_none()
        
        if about:
            about_data = schemas.AboutPublic(
                content=about.content,
                updated_at=about.updated_at
            )
            await self.redis.setex(cache_key, 3600, about_data.model_dump_json())
            return about_data
        
        return None
    
    async def get_admission_info(self, year: Optional[int] = None) -> Optional[schemas.AdmissionYear]:
        """Получить информацию о приеме за указанный год (или текущий)"""
        
        if not year:
            # Берем текущий год
            result = await self.db.execute(
                select(AdmissionInfo)
                .where(AdmissionInfo.is_current == True)
                .order_by(AdmissionInfo.year.desc())
                .limit(1)
            )
        else:
            result = await self.db.execute(
                select(AdmissionInfo).where(AdmissionInfo.year == year)
            )
        
        admission = result.scalar_one_or_none()
        
        if admission:
            return schemas.AdmissionYear(
                year=admission.year,
                data=admission.data
            )
        
        return None