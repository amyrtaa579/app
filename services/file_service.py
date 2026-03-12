import os
import shutil
import magic  # pip install python-magic
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Optional, BinaryIO
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

class FileService:
    """Сервис для работы с файлами в локальной файловой системе"""
    
    def __init__(self):
        self.base_dir = Path(settings.STATIC_FILES_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем необходимые поддиректории
        self.images_dir = self.base_dir / "uploads" / "images"
        self.documents_dir = self.base_dir / "uploads" / "documents"
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_today_path(self, base_path: Path) -> Path:
        """Возвращает путь вида /base/2026/03/12/"""
        today = datetime.now()
        return base_path / str(today.year) / f"{today.month:02d}" / f"{today.day:02d}"
    
    def _generate_filename(self, original_filename: str) -> str:
        """Генерирует уникальное имя файла"""
        ext = Path(original_filename).suffix.lower()
        return f"{uuid4().hex}{ext}"
    
    def _validate_file_type(self, file: UploadFile, category: str) -> None:
        """Валидация типа файла с помощью python-magic"""
        # Читаем первые байты для определения MIME-типа
        content = file.file.read(2048)
        file.file.seek(0)  # Возвращаем указатель в начало
        
        mime = magic.from_buffer(content, mime=True)
        
        if category == "image":
            if mime not in settings.ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image type. Allowed: {settings.ALLOWED_IMAGE_TYPES}"
                )
        elif category == "document":
            if mime not in settings.ALLOWED_DOCUMENT_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document type. Allowed: {settings.ALLOWED_DOCUMENT_TYPES}"
                )
    
    async def save_image(
        self,
        file: UploadFile,
        subfolder: str = "general"
    ) -> dict:
        """
        Сохраняет изображение и возвращает информацию о нем.
        
        Args:
            file: Загруженный файл
            subfolder: Подпапка (specialties, facts, news, results)
            
        Returns:
            dict: {
                "url": "/static/uploads/images/specialties/2026/03/12/uuid4.jpg",
                "file_path": "полный путь на сервере",
                "file_size": 12345,
                "mime_type": "image/jpeg",
                "original_name": "original.jpg"
            }
        """
        # Валидация типа
        self._validate_file_type(file, "image")
        
        # Проверка размера
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE / (1024*1024)} MB"
            )
        
        # Создаем путь для сохранения
        target_dir = self._get_today_path(self.images_dir / subfolder)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        filename = self._generate_filename(file.filename)
        file_path = target_dir / filename
        
        # Сохраняем файл
        try:
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save file: {e}"
            )
        finally:
            await file.close()
        
        # Формируем URL
        relative_path = f"uploads/images/{subfolder}/{file_path.relative_to(self.images_dir.parent.parent)}"
        url = f"{settings.STATIC_URL}/{relative_path}"
        
        return {
            "url": url,
            "file_path": str(file_path),
            "file_size": file_size,
            "mime_type": file.content_type,
            "original_name": file.filename
        }
    
    async def save_document(
        self,
        file: UploadFile,
        category: str = "general"
    ) -> dict:
        """
        Сохраняет документ и возвращает информацию о нем.
        """
        # Валидация типа
        self._validate_file_type(file, "document")
        
        # Проверка размера
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE / (1024*1024)} MB"
            )
        
        # Создаем путь для сохранения
        target_dir = self._get_today_path(self.documents_dir / category)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        filename = self._generate_filename(file.filename)
        file_path = target_dir / filename
        
        # Сохраняем файл
        try:
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save file: {e}"
            )
        finally:
            await file.close()
        
        # Формируем URL
        relative_path = f"uploads/documents/{category}/{file_path.relative_to(self.documents_dir.parent.parent)}"
        url = f"{settings.STATIC_URL}/{relative_path}"
        
        return {
            "url": url,
            "file_path": str(file_path),
            "file_size": file_size,
            "mime_type": file.content_type,
            "original_name": file.filename
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Удаляет файл по полному пути"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def delete_file_by_url(self, url: str) -> bool:
        """Удаляет файл по URL"""
        # Извлекаем относительный путь из URL
        relative_path = url.replace(settings.STATIC_URL, "").lstrip("/")
        full_path = self.base_dir / relative_path
        return self.delete_file(str(full_path))

# Создаем глобальный экземпляр сервиса
file_service = FileService()