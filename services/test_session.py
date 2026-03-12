import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis

class TestSessionService:
    """Сервис для управления сессиями прохождения теста в Redis"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.session_ttl = 3600  # 1 час на прохождение теста
    
    def _get_session_key(self, session_id: str) -> str:
        return f"test:session:{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        return f"test:user:{user_id}:sessions"
    
    async def create_session(self, user_id: str) -> str:
        """
        Создает новую сессию тестирования для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            session_id: Уникальный ID сессии
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "current_question": 0,
            "answers": [],  # Список ответов {question_id, option_ids}
            "completed": False,
            "result": None
        }
        
        key = self._get_session_key(session_id)
        await self.redis.setex(key, self.session_ttl, json.dumps(session_data, default=str))
        
        # Добавляем в список сессий пользователя
        user_sessions_key = self._get_user_sessions_key(user_id)
        await self.redis.sadd(user_sessions_key, session_id)
        await self.redis.expire(user_sessions_key, 86400)  # 24 часа
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные сессии по ID"""
        key = self._get_session_key(session_id)
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Обновляет данные сессии"""
        key = self._get_session_key(session_id)
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        session.update(updates)
        await self.redis.setex(key, self.session_ttl, json.dumps(session, default=str))
        return True
    
    async def add_answer(
        self,
        session_id: str,
        question_id: int,
        option_ids: List[int]
    ) -> bool:
        """Добавляет ответ на вопрос"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Проверяем, не отвечали ли уже на этот вопрос
        for answer in session["answers"]:
            if answer["question_id"] == question_id:
                return False
        
        session["answers"].append({
            "question_id": question_id,
            "option_ids": option_ids,
            "answered_at": datetime.utcnow().isoformat()
        })
        
        session["current_question"] = len(session["answers"])
        
        return await self.update_session(session_id, session)
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Получает все сессии пользователя"""
        user_sessions_key = self._get_user_sessions_key(user_id)
        session_ids = await self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    async def complete_session(
        self,
        session_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """Отмечает сессию как завершенную"""
        return await self.update_session(session_id, {
            "completed": True,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        })
    
    async def delete_session(self, session_id: str) -> bool:
        """Удаляет сессию"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        key = self._get_session_key(session_id)
        await self.redis.delete(key)
        
        # Удаляем из списка пользователя
        user_sessions_key = self._get_user_sessions_key(session["user_id"])
        await self.redis.srem(user_sessions_key, session_id)
        
        return True
    
    async def cleanup_old_sessions(self) -> int:
        """Очищает старые сессии (вызывается периодически)"""
        # Redis сам удаляет по TTL, но можно дополнительно очищать
        count = 0
        # TODO: реализовать при необходимости
        return count