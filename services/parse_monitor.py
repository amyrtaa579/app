from typing import Dict, Any, List
from datetime import datetime, timedelta
from redis.asyncio import Redis
import json

class ParseMonitor:
    """Мониторинг работы парсера"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.stats_key = "parse:stats"
        self.errors_key = "parse:errors"
    
    async def record_success(self, task_id: str, news_count: int):
        """Записывает успешный парсинг"""
        stats = {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "news_count": news_count,
            "status": "success"
        }
        
        await self.redis.lpush(self.stats_key, json.dumps(stats, default=str))
        await self.redis.ltrim(self.stats_key, 0, 99)  # Храним только 100 записей
    
    async def record_error(self, task_id: str, error: str):
        """Записывает ошибку парсинга"""
        error_data = {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
            "status": "failed"
        }
        
        await self.redis.lpush(self.errors_key, json.dumps(error_data, default=str))
        await self.redis.ltrim(self.errors_key, 0, 49)  # Храним только 50 ошибок
    
    async def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Получает статистику парсинга"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Получаем все записи
        stats_data = await self.redis.lrange(self.stats_key, 0, -1)
        errors_data = await self.redis.lrange(self.errors_key, 0, -1)
        
        stats = [json.loads(s) for s in stats_data]
        errors = [json.loads(e) for e in errors_data]
        
        # Фильтруем по дате
        stats = [
            s for s in stats
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]
        errors = [
            e for e in errors
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        
        total_parsed = sum(s.get("news_count", 0) for s in stats)
        
        return {
            "total_parses": len(stats),
            "total_errors": len(errors),
            "total_news_parsed": total_parsed,
            "average_news_per_parse": total_parsed / len(stats) if stats else 0,
            "success_rate": (len(stats) / (len(stats) + len(errors))) * 100 if (stats or errors) else 0,
            "last_parse": stats[0] if stats else None,
            "last_error": errors[0] if errors else None
        }
    
    async def clear_old_stats(self, days: int = 30):
        """Очищает старую статистику"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        for key in [self.stats_key, self.errors_key]:
            data = await self.redis.lrange(key, 0, -1)
            
            for item in data:
                record = json.loads(item)
                record_date = datetime.fromisoformat(record["timestamp"])
                
                if record_date < cutoff:
                    await self.redis.lrem(key, 1, item)