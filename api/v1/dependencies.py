from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, get_redis
from app.core.security import decode_token
from app.models import Admin
from app.services.file_service import file_service

# Пагинация
async def pagination_params(
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(100, ge=1, le=1000, description="Сколько вернуть")
) -> tuple[int, int]:
    return skip, limit

PaginationDep = Annotated[tuple[int, int], Depends(pagination_params)]

# Аутентификация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login")

async def get_current_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    admin_id: Optional[int] = payload.get("sub")
    
    if admin_id is None:
        raise credentials_exception
    
    result = await db.execute(
        select(Admin).where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    
    if admin is None:
        raise credentials_exception
    
    return admin

CurrentAdminDep = Annotated[Admin, Depends(get_current_admin)]

# Redis
RedisDep = Annotated[AsyncSession, Depends(get_redis)]

# File service
FileServiceDep = Annotated[FileService, Depends(lambda: file_service)]