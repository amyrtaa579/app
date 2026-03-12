from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
from redis.asyncio import Redis
from celery.result import AsyncResult

from app.worker import celery_app, parse_news_task, TaskStatus
from app.schemas.parser import ParseTask, ParsedNews

class ParseTaskService:
    """Сервис для управления задачами парсинга"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.tasks_key = "parse:tasks"
        self.results_ttl = 86400  # 24 часа
    
    async def create_parse_task(
        self,
        max_news: int = 10,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Создает новую задачу на парсинг
        """
        # Запускаем Celery задачу
        task = parse_news_task.delay(max_news, days_back)
        
        task_data = {
            "task_id": task.id,
            "status": TaskStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "max_news": max_news,
            "days_back": days_back
        }
        
        # Сохраняем в Redis
        await self.redis.hset(
            self.tasks_key,
            task.id,
            json.dumps(task_data, default=str)
        )
        await self.redis.expire(self.tasks_key, self.results_ttl)
        
        return task_data
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает статус задачи
        """
        # Пробуем получить из Redis
        task_data = await self.redis.hget(self.tasks_key, task_id)
        
        if task_data:
            result = json.loads(task_data)
            
            # Если задача еще выполняется, получаем актуальный статус из Celery
            if result["status"] in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                async_result = AsyncResult(task_id, app=celery_app)
                
                if async_result.ready():
                    if async_result.successful():
                        result["status"] = TaskStatus.COMPLETED
                        result["result"] = async_result.get()
                    else:
                        result["status"] = TaskStatus.FAILED
                        result["error"] = str(async_result.info)
                    
                    # Обновляем в Redis
                    await self.redis.hset(
                        self.tasks_key,
                        task_id,
                        json.dumps(result, default=str)
                    )
            
            return result
        
        return None
    
    async def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает список всех задач
        """
        tasks_data = await self.redis.hgetall(self.tasks_key)
        
        tasks = []
        for task_id, data in tasks_data.items():
            task = json.loads(data)
            tasks.append(task)
        
        # Сортируем по дате создания (сначала новые)
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        return tasks[:limit]
    
    async def cleanup_old_tasks(self, days: int = 7):
        """
        Очищает старые задачи
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        tasks_data = await self.redis.hgetall(self.tasks_key)
        
        for task_id, data in tasks_data.items():
            task = json.loads(data)
            created_at = datetime.fromisoformat(task["created_at"])
            
            if created_at < cutoff:
                await self.redis.hdel(self.tasks_key, task_id)
    
    async def get_last_parse_result(self) -> Optional[Dict[str, Any]]:
        """
        Получает результат последнего успешного парсинга
        """
        tasks = await self.get_all_tasks(10)
        
        for task in tasks:
            if task.get("status") == TaskStatus.COMPLETED and task.get("result"):
                return task
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Отменяет выполняющуюся задачу
        """
        async_result = AsyncResult(task_id, app=celery_app)
        
        if not async_result.ready():
            async_result.revoke(terminate=True)
            
            # Обновляем статус в Redis
            task_data = await self.redis.hget(self.tasks_key, task_id)
            if task_data:
                task = json.loads(task_data)
                task["status"] = "cancelled"
                await self.redis.hset(
                    self.tasks_key,
                    task_id,
                    json.dumps(task, default=str)
                )
            
            return True
        
        return False