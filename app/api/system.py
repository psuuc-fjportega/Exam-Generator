from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_service import ai_service
from app.api.deps import get_current_active_teacher
from app.models.user import User

router = APIRouter()


class AIStatusResponse(BaseModel):
    ai_configured: bool
    model_name: str
    key_preview: Optional[str] = None
    message: str


class ConfigureKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="Google Gemini API Key")


@router.get("/ai-status", response_model=AIStatusResponse)
def get_ai_status() -> Any:
    """Check whether the Gemini API key is configured and ready for generation."""
    key = settings.get_effective_ai_api_key()
    configured = bool(key)
    preview = None
    if key and len(key) >= 8:
        preview = f"{key[:4]}...{key[-4:]}"

    message = (
        "Gemini AI service is configured and ready."
        if configured
        else "Gemini API key is not configured. Set AI_API_KEY in your environment or configure it in the web interface."
    )

    return AIStatusResponse(
        ai_configured=configured,
        model_name=getattr(settings, "AI_MODEL_NAME", "gemini-3.5-flash-lite"),
        key_preview=preview,
        message=message,
    )


@router.post("/configure-key")
def configure_ai_key(
    request: ConfigureKeyRequest,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    """Configure or update the Gemini API key at runtime."""
    clean_key = request.api_key.strip()
    if not clean_key or clean_key == "your_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid Gemini API key.",
        )

    # Test key initialization
    try:
        from google import genai
        test_client = genai.Client(api_key=clean_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to initialize Gemini client with provided key: {str(exc)}",
        )

    # Update settings and reset service cached client
    settings.update_ai_api_key(clean_key, persist_to_env=True)
    ai_service._cached_key = None
    ai_service._client = None

    return {
        "status": "success",
        "ai_configured": True,
        "key_preview": f"{clean_key[:4]}...{clean_key[-4:]}",
        "message": "Gemini API key has been configured successfully.",
    }
