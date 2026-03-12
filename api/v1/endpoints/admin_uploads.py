from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_current_admin, FileServiceDep
from app.services.file_service import FileService

router = APIRouter(prefix="/admin/uploads", tags=["Admin Uploads"])

@router.post("/image/{subfolder}")
async def upload_image(
    subfolder: str,
    file: Annotated[UploadFile, File(description="Image file to upload")],
    file_service: FileServiceDep,
    current_admin: Annotated[dict, Depends(get_current_admin)]
):
    """
    Загружает изображение в указанную подпапку.
    
    Подпапки: specialties, facts, news, results, general
    """
    # Проверяем допустимость подпапки
    allowed_subfolders = ["specialties", "facts", "news", "results", "general"]
    if subfolder not in allowed_subfolders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subfolder. Allowed: {allowed_subfolders}"
        )
    
    result = await file_service.save_image(file, subfolder)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "url": result["url"],
            "file_size": result["file_size"],
            "mime_type": result["mime_type"],
            "message": "Image uploaded successfully"
        }
    )

@router.post("/document/{category}")
async def upload_document(
    category: str,
    file: Annotated[UploadFile, File(description="Document file to upload")],
    file_service: FileServiceDep,
    current_admin: Annotated[dict, Depends(get_current_admin)]
):
    """
    Загружает документ в указанную категорию.
    
    Категории: 9_class, 11_class, parents, general
    """
    allowed_categories = ["9_class", "11_class", "parents", "general"]
    if category not in allowed_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Allowed: {allowed_categories}"
        )
    
    result = await file_service.save_document(file, category)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "url": result["url"],
            "file_size": result["file_size"],
            "mime_type": result["mime_type"],
            "message": "Document uploaded successfully"
        }
    )

@router.delete("/file")
async def delete_file(
    url: str,
    file_service: FileServiceDep,
    current_admin: Annotated[dict, Depends(get_current_admin)]
):
    """
    Удаляет файл по его URL.
    """
    success = file_service.delete_file_by_url(url)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )
    
    return {"message": "File deleted successfully"}