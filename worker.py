from celery import Celery
from celery.signals import task_failure, task_success
import asyncio
from datetime import datetime
import logging
from typing import Dict, Any

from app.core.config import settings
from app.services.news_parser import TPGKNewsParser
from app.services.admin_news import NewsAdminService
from app.core.database import AsyncSessionLocal
from app.schemas import admin as schemas
from celery.schedules import crontab
from app.services.statistics import StatisticsService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Celery приложение
celery_app = Celery(
    'tpgk_bot',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.worker']
)

# Настройки Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_store_errors_even_if_ignored=True,
)

@celery_app.task(name="aggregate_daily_stats")
def aggregate_daily_stats():
    """Ежедневная агрегация статистики"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _aggregate():
        async with AsyncSessionLocal() as db:
            service = StatisticsService(db)
            await service.aggregate_daily_stats()
    
    loop.run_until_complete(_aggregate())
    loop.close()
    
# Настройки для периодических задач
celery_app.conf.beat_schedule = {
    # Парсинг новостей каждый день в 8:00
    'parse-news-daily': {
        'task': 'parse_news_task',
        'schedule': crontab(hour=8, minute=0),
        'args': (10, 7)  # max_news=10, days_back=7
    },
    
    # Очистка старых задач каждую неделю
    'cleanup-old-tasks-weekly': {
        'task': 'cleanup_old_tasks',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Понедельник 3:00
    },
}

# Добавляем в расписание
celery_app.conf.beat_schedule.update({
    # Агрегация статистики каждый день в 23:59
    'aggregate-stats-daily': {
        'task': 'aggregate_daily_stats',
        'schedule': crontab(hour=23, minute=59),
    },
})

class TaskStatus:
    """Статусы задач"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@celery_app.task(bind=True, name="parse_news_task")
def parse_news_task(self, max_news: int = 10, days_back: int = 30):
    """
    Задача для парсинга новостей
    """
    task_id = self.request.id
    logger.info(f"Starting parse news task {task_id}")
    
    # Обновляем статус
    self.update_state(
        state=TaskStatus.RUNNING,
        meta={'status': 'Parsing news...'}
    )
    
    try:
        # Запускаем асинхронный парсер в синхронном контексте
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        parser = TPGKNewsParser()
        parsed_news = loop.run_until_complete(
            parser.parse_news(max_news=max_news, days_back=days_back)
        )
        
        # Сохраняем в базу
        saved_count = loop.run_until_complete(
            save_parsed_news(parsed_news)
        )
        
        loop.close()
        
        logger.info(f"Parse task {task_id} completed. Saved {saved_count} news")
        
        return {
            'status': TaskStatus.COMPLETED,
            'task_id': task_id,
            'parsed_count': len(parsed_news),
            'saved_count': saved_count,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Parse task {task_id} failed: {e}", exc_info=True)
        
        self.update_state(
            state=TaskStatus.FAILED,
            meta={'error': str(e)}
        )
        
        return {
            'status': TaskStatus.FAILED,
            'task_id': task_id,
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        }

async def save_parsed_news(parsed_news_list):
    """
    Сохраняет распарсенные новости в базу данных
    """
    saved_count = 0
    
    async with AsyncSessionLocal() as db:
        # Импортируем здесь чтобы избежать циклических импортов
        from app.services.admin_news import NewsAdminService
        from app.core.database import get_redis
        
        redis = await get_redis()
        service = NewsAdminService(db, redis)
        
        for parsed in parsed_news_list:
            try:
                # Проверяем, есть ли уже такая новость
                existing = await db.execute(
                    select(News).where(News.source_url == parsed.source_url)
                )
                if existing.scalar_one_or_none():
                    logger.info(f"News already exists: {parsed.title}")
                    continue
                
                # Создаем схему для создания новости
                news_create = schemas.NewsAdminCreate(
                    title=parsed.title,
                    date=parsed.date,
                    content_html=parsed.content_html,
                    preview_text=parsed.preview_text,
                    source_url=parsed.source_url,
                    is_published=True,
                    images=[
                        schemas.NewsImageAdmin(
                            image_url=img.url,
                            caption=img.caption,
                            sort_order=i
                        )
                        for i, img in enumerate(parsed.images)
                    ]
                )
                
                # Сохраняем
                await service.create_with_images(news_create)
                saved_count += 1
                logger.info(f"Saved news: {parsed.title}")
                
            except Exception as e:
                logger.error(f"Error saving news {parsed.title}: {e}")
                continue
    
    return saved_count


@celery_app.task(name="cleanup_old_tasks")
def cleanup_old_tasks():
    """
    Периодическая задача для очистки старых записей о задачах
    """
    # Очистка результатов задач старше 7 дней
    # Реализуется через настройки Redis или отдельную логику
    pass


# Сигналы для мониторинга
@task_success.connect(sender=parse_news_task)
def task_succeeded_handler(sender=None, result=None, **kwargs):
    logger.info(f"Task {sender.request.id} succeeded with result: {result}")

@task_failure.connect(sender=parse_news_task)
def task_failed_handler(sender=None, task_id=None, exception=None, **kwargs):
    logger.error(f"Task {task_id} failed: {exception}")