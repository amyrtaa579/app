from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models import Admin
from app.schemas.token import Token
from app.core.config import settings

router = APIRouter(tags=["Authentication"])

@router.post("/admin/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Вход администратора в систему.
    Получает login/password, возвращает JWT токен.
    """
    # Ищем админа по логину (email)
    result = await db.execute(
        select(Admin).where(Admin.login == form_data.username)
    )
    admin = result.scalar_one_or_none()
    
    # Проверяем пароль
    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Обновляем время последнего входа
    admin.last_login = datetime.utcnow()
    await db.commit()
    
    # Создаем токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(admin.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": admin.id,
            "login": admin.login,
            "full_name": admin.full_name
        }
    }