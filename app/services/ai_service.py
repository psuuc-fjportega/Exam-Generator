import json
import logging
import os
import sys
from typing import Any, Dict, Optional
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self._cached_key: Optional[str] = None
        self._client: Optional[genai.Client] = None

    @staticmethod
    def is_test_environment() -> bool:
        """Detect whether code is running inside a test runner (e.g. pytest)."""
        return (
            "pytest" in sys.modules 
            or os.environ.get("TESTING") == "1" 
            or "PYTEST_CURRENT_TEST" in os.environ
        )

    def get_client(self) -> Optional[genai.Client]:
        """Dynamically get or initialize the Gemini client using active settings / environment."""
        key = settings.get_effective_ai_api_key()
        if not key:
            self._client = None
            self._cached_key = None
            return None

        if self._client is None or self._cached_key != key:
            try:
                self._client = genai.Client(api_key=key)
                self._cached_key = key
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
                self._cached_key = None
        return self._client

    @property
    def client(self) -> Optional[genai.Client]:
        return self.get_client()

    def is_configured(self) -> bool:
        """Check whether a valid Gemini API key is configured and client can be initialized."""
        return self.get_client() is not None

    def generate_structured_json(
        self, 
        prompt: str, 
        response_schema: Any, 
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON using Gemini API.
        """
        if self.is_test_environment() and os.environ.get("USE_LIVE_AI") != "1":
            logger.info("Test environment detected. Returning mock response for test isolation.")
            return self._get_mock_response(response_schema)

        active_model = model_name or getattr(settings, "AI_MODEL_NAME", "gemini-3.5-flash-lite")
        client = self.get_client()

        if not client:
            raise RuntimeError(
                "Gemini AI API Key is not configured. Please set the AI_API_KEY or GEMINI_API_KEY "
                "environment variable in your server configuration (e.g., Render Dashboard or .env file), "
                "or configure it via the web interface."
            )
            
        try:
            response = client.models.generate_content(
                model=active_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error calling Gemini API ({active_model}): {str(e)}")
            raise e
            
    def _get_mock_response(self, response_schema: Any = None) -> Dict[str, Any]:
        schema_name = getattr(response_schema, "__name__", "")
        if schema_name == "AIValidationOutput":
            return {
                "valid": True,
                "confidence": 0.92,
                "issues": [],
                "source_supported": True,
                "difficulty_appropriate": True,
            }
        elif schema_name in {"DocumentAnalysisOutput", "DocumentAnalysis"}:
            return {
                "title_suggestion": "Comprehensive Examination: Fundamental Concepts",
                "summary": "This document covers fundamental concepts and principles presented in the course material.",
                "key_topics": ["Overview and Core Principles", "Key Methodologies", "Practical Applications"],
                "key_concepts": ["Foundational Theory", "System Architecture", "Operational Workflow"],
                "learning_objectives": [
                    "Understand core principles and theoretical mechanisms",
                    "Apply learned methodologies to practical scenarios",
                    "Analyze and evaluate outcomes effectively"
                ],
                "estimated_difficulty": "medium",
                "difficulty_reasoning": "The material introduces standard conceptual foundations with moderate technical depth.",
                "recommended_total_questions": 10,
                "recommended_time_minutes": 60,
                "recommended_distribution": {
                    "multiple_choice": 4,
                    "true_false": 2,
                    "identification": 2,
                    "essay": 1,
                    "matching": 1
                }
            }
        return {
            "questions": [
                {
                    "question_text": "This is a mock AI question based on the material.",
                    "question_type": "multiple_choice",
                    "difficulty": "medium",
                    "topic": "Mock Topic",
                    "choices": [
                        {"text": "Correct mock answer", "is_correct": True},
                        {"text": "Wrong mock answer 1", "is_correct": False},
                        {"text": "Wrong mock answer 2", "is_correct": False},
                        {"text": "Wrong mock answer 3", "is_correct": False}
                    ],
                    "explanation": "This is a mock explanation.",
                    "source_chunk_ids": []
                }
            ]
        }

ai_service = AIService()
