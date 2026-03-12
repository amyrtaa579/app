from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
from typing import Optional
from uuid import uuid4

from app.services.statistics import StatisticsService
from app.core.database import AsyncSessionLocal

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Генерируем ID запроса
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Запоминаем время начала
        start_time = time.time()
        
        # Получаем IP и User-Agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Выполняем запрос
        try:
            response = await call_next(request)
            
            # Логируем только определенные эндпоинты
            if self._should_log(request.url.path):
                await self._log_request(
                    request=request,
                    response=response,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    duration=time.time() - start_time
                )
            
            return response
            
        except Exception as e:
            # Логируем ошибки
            await self._log_error(
                request=request,
                error=e,
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise
    
    def _should_log(self, path: str) -> bool:
        """Проверяет, нужно ли логировать запрос"""
        # Не логируем статику и служебные эндпоинты
        exclude_paths = [
            "/static/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        ]
        
        for exclude in exclude_paths:
            if path.startswith(exclude):
                return False
        
        return True
    
    async def _log_request(
        self,
        request: Request,
        response: Response,
        ip_address: Optional[str],
        user_agent: Optional[str],
        duration: float
    ):
        """Логирует успешный запрос"""
        # Здесь можно добавить запись в отдельную таблицу логов
        # или отправку в систему мониторинга
        pass
    
    async def _log_error(
        self,
        request: Request,
        error: Exception,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Логирует ошибку"""
        # Здесь можно добавить запись ошибки
        pass

class UserActionMiddleware(BaseHTTPMiddleware):
    """Middleware для отслеживания действий пользователей"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Пытаемся определить действие пользователя
        if request.method == "GET" and request.url.path.startswith("/api/v1/public"):
            await self._track_user_action(request, response)
        
        return response
    
    async def _track_user_action(self, request: Request, response: Response):
        """Отслеживает действие пользователя"""
        # Получаем user_id из заголовка (Telegram ID)
        user_id = request.headers.get("X-Telegram-User-ID")
        if not user_id:
            return
        
        path = request.url.path
        ip_address = request.client.host if request.client else None
        
        # Определяем тип действия
        action = None
        entity_type = None
        entity_id = None
        
        if "/specialties/" in path and request.method == "GET":
            # Просмотр специальности
            parts = path.split("/")
            if len(parts) >= 5 and parts[-2] == "specialties":
                try:
                    entity_id = int(parts[-1])
                    action = "view"
                    entity_type = "specialty"
                except:
                    pass
        
        elif "/documents/" in path and "/download" in path:
            # Скачивание документа
            parts = path.split("/")
            if len(parts) >= 5 and parts[-2] == "documents":
                try:
                    entity_id = int(parts[-1].replace("/download", ""))
                    action = "download"
                    entity_type = "document"
                except:
                    pass
        
        if action and entity_type and entity_id:
            # Асинхронно логируем действие
            async with AsyncSessionLocal() as db:
                stats_service = StatisticsService(db)
                await stats_service.log_user_action(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=ip_address
                )