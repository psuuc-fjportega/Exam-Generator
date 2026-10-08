import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException
from typing import Tuple
from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain"
}

def validate_file(file: UploadFile) -> Tuple[str, str]:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension {ext} not allowed.")
    return ext, file.content_type

async def save_upload_file(upload_file: UploadFile, destination_dir: str) -> Tuple[str, str, int]:
    os.makedirs(destination_dir, exist_ok=True)
    
    # Check size limit
    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)
    
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = os.path.splitext(upload_file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(destination_dir, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return unique_filename, file_path, file_size
