from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
import json

from app.models import TestQuestion, TestOption, TestResult, Specialty
from app.schemas import public as schemas
from app.services.test_session import TestSessionService

class TestService:
    """Основной сервис для профориентационного тестирования"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.session_service = TestSessionService(redis_client)
    
    async def get_questions(self) -> List[TestQuestion]:
        """Получить все вопросы теста с вариантами"""
        cache_key = "test:questions:full"
        cached = await self.redis.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            # Здесь нужно будет восстановить объекты
            return [self._dict_to_question(q) for q in data]
        
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
        
        # Кэшируем
        if questions:
            questions_data = []
            for q in questions:
                q_dict = {
                    "id": q.id,
                    "text": q.text,
                    "image_url": str(q.image_url) if q.image_url else None,
                    "type": q.type,
                    "sort_order": q.sort_order,
                    "options": [
                        {
                            "id": o.id,
                            "text": o.text,
                            "image_url": str(o.image_url) if o.image_url else None,
                            "points": o.points,
                            "sort_order": o.sort_order
                        }
                        for o in q.options
                    ]
                }
                questions_data.append(q_dict)
            
            await self.redis.setex(cache_key, 3600, json.dumps(questions_data, default=str))
        
        return questions
    
    def _dict_to_question(self, data: Dict) -> TestQuestion:
        """Восстанавливает объект вопроса из словаря"""
        # Упрощенная версия для кэша
        question = TestQuestion(**{k: v for k, v in data.items() if k != "options"})
        question.options = [TestOption(**o) for o in data["options"]]
        return question
    
    async def calculate_result(
        self,
        answers: List[schemas.TestAnswer]
    ) -> Tuple[TestResult, int, Dict[int, int]]:
        """
        Рассчитывает результат теста по ответам.
        
        Returns:
            Tuple[TestResult, int, Dict]: (результат, сумма баллов, баллы по вопросам)
        """
        total_points = 0
        question_points = {}
        
        # Получаем все варианты ответов одним запросом для оптимизации
        option_ids = []
        for answer in answers:
            option_ids.extend(answer.option_ids)
        
        result = await self.db.execute(
            select(TestOption).where(TestOption.id.in_(option_ids))
        )
        options = result.scalars().all()
        options_dict = {o.id: o.points for o in options}
        
        # Суммируем баллы
        for answer in answers:
            points = sum(options_dict.get(opt_id, 0) for opt_id in answer.option_ids)
            total_points += points
            question_points[answer.question_id] = points
        
        # Находим подходящий результат
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
            # Если результат не найден, берем ближайший
            result = await self.db.execute(
                select(TestResult)
                .order_by(TestResult.min_score)
            )
            all_results = result.scalars().all()
            
            # Находим результат с ближайшим диапазоном
            test_result = min(
                all_results,
                key=lambda r: min(
                    abs(r.min_score - total_points),
                    abs(r.max_score - total_points)
                )
            )
        
        return test_result, total_points, question_points
    
    async def get_result_for_user(
        self,
        user_id: str,
        answers: List[schemas.TestAnswer]
    ) -> Dict[str, Any]:
        """
        Получает результат теста для пользователя с сохранением в истории.
        """
        # Рассчитываем результат
        test_result, total_points, question_points = await self.calculate_result(answers)
        
        # Парсим сильные стороны
        strengths = []
        if test_result.strengths:
            try:
                strengths = json.loads(test_result.strengths)
            except:
                strengths = [test_result.strengths]
        
        # Формируем результат
        result_data = {
            "specialty_id": test_result.specialty_id,
            "specialty_name": test_result.specialty.name if test_result.specialty else "",
            "title": test_result.title,
            "description": test_result.description,
            "strengths": strengths,
            "image_url": str(test_result.image_url) if test_result.image_url else None,
            "total_points": total_points,
            "question_points": question_points,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return result_data
    
    async def start_test(self, user_id: str) -> str:
        """Начинает новый тест для пользователя"""
        return await self.session_service.create_session(user_id)
    
    async def save_answer(
        self,
        session_id: str,
        question_id: int,
        option_ids: List[int]
    ) -> bool:
        """Сохраняет ответ в текущей сессии"""
        return await self.session_service.add_answer(session_id, question_id, option_ids)
    
    async def finish_test(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Завершает тест и возвращает результат"""
        session = await self.session_service.get_session(session_id)
        if not session or session["completed"]:
            return None
        
        # Преобразуем ответы из сессии
        answers = [
            schemas.TestAnswer(
                question_id=a["question_id"],
                option_ids=a["option_ids"]
            )
            for a in session["answers"]
        ]
        
        # Получаем результат
        result = await self.get_result_for_user(session["user_id"], answers)
        
        # Отмечаем сессию как завершенную
        await self.session_service.complete_session(session_id, result)
        
        return result
    
    async def get_test_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получает прогресс прохождения теста"""
        session = await self.session_service.get_session(session_id)
        if not session:
            return None
        
        # Получаем общее количество вопросов
        questions = await self.get_questions()
        total_questions = len(questions)
        
        return {
            "session_id": session["session_id"],
            "current_question": session["current_question"],
            "total_questions": total_questions,
            "progress_percent": (session["current_question"] / total_questions) * 100 if total_questions > 0 else 0,
            "completed": session["completed"],
            "has_result": session["result"] is not None
        }
    
    async def get_test_statistics(self) -> Dict[str, Any]:
        """Получает статистику прохождения тестов"""
        # Получаем все сессии из Redis (сложно, можно хранить счетчики отдельно)
        # Для простоты вернем базовую статистику
        
        # Количество прохождений за сегодня/неделю/месяц
        # Можно хранить в отдельном ключе Redis
        
        today_key = f"test:stats:{datetime.utcnow().date()}"
        week_key = f"test:stats:week:{datetime.utcnow().isocalendar()[1]}"
        
        today_count = await self.redis.get(today_key) or 0
        week_count = await self.redis.get(week_key) or 0
        
        # Популярные результаты
        popular_results = await self._get_popular_results()
        
        return {
            "total_tests_today": int(today_count),
            "total_tests_this_week": int(week_count),
            "popular_results": popular_results
        }
    
    async def _get_popular_results(self, limit: int = 5) -> List[Dict]:
        """Получает самые популярные результаты"""
        # Здесь можно собирать статистику из БД
        # Например, добавить поле completion_count в TestResult
        return []
    
    async def increment_test_counter(self):
        """Увеличивает счетчик прохождений теста"""
        today = datetime.utcnow().date()
        week = datetime.utcnow().isocalendar()[1]
        
        today_key = f"test:stats:{today}"
        week_key = f"test:stats:week:{week}"
        
        await self.redis.incr(today_key)
        await self.redis.incr(week_key)
        
        # Устанавливаем TTL
        await self.redis.expire(today_key, 86400 * 2)  # 2 дня
        await self.redis.expire(week_key, 86400 * 14)  # 2 недели