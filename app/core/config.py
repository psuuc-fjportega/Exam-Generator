import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine absolute path to project root .env
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Examination Generator"
    DATABASE_URL: str = "sqlite:///./exam_generator.db"
    
    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    AI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-3.5-flash-lite"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_effective_ai_api_key(self) -> Optional[str]:
        """Return the effective AI API key checking all possible env vars and fields."""
        key = (
            self.AI_API_KEY
            or self.GEMINI_API_KEY
            or self.GOOGLE_API_KEY
            or os.environ.get("AI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if key and key.strip() and key.strip() != "your_api_key_here":
            return key.strip()
        return None

    def update_ai_api_key(self, new_key: str, persist_to_env: bool = True) -> None:
        """Update the active AI API key in settings, os.environ, and optionally .env file."""
        import sys
        clean_key = new_key.strip()
        self.AI_API_KEY = clean_key
        os.environ["AI_API_KEY"] = clean_key
        os.environ["GEMINI_API_KEY"] = clean_key

        is_testing = (
            "pytest" in sys.modules 
            or os.environ.get("TESTING") == "1" 
            or "PYTEST_CURRENT_TEST" in os.environ
        )
        if persist_to_env and not is_testing and _ENV_FILE.parent.exists():
            try:
                lines = []
                key_found = False
                if _ENV_FILE.exists():
                    with open(_ENV_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                
                new_lines = []
                for line in lines:
                    if line.startswith("AI_API_KEY="):
                        new_lines.append(f"AI_API_KEY={clean_key}\n")
                        key_found = True
                    else:
                        new_lines.append(line)
                        
                if not key_found:
                    new_lines.append(f"AI_API_KEY={clean_key}\n")
                    
                with open(_ENV_FILE, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            except Exception:
                pass # Gracefully handle read-only environments like container mounts

settings = Settings()

