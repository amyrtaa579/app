from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    admin_uploads,
    admin_specialties,
    admin_test,
    admin_documents,
    admin_faqs,
    admin_news,
    admin_info,
    admin_parse,  # <-- Добавляем
    public,
    test,
)

api_router = APIRouter()

# Публичные эндпоинты (для бота)
api_router.include_router(public.router)

# Тестирование
api_router.include_router(test.router)

# Аутентификация
api_router.include_router(auth.router)

# Админские эндпоинты
api_router.include_router(admin_uploads.router)
api_router.include_router(admin_specialties.router)
api_router.include_router(admin_test.router)
api_router.include_router(admin_documents.router)
api_router.include_router(admin_faqs.router)
api_router.include_router(admin_news.router)
api_router.include_router(admin_info.router)
api_router.include_router(admin_parse.router)  # <-- Добавляем