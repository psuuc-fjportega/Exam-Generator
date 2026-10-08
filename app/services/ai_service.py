import json
import logging
from typing import Any, Dict
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        if self.api_key and self.api_key != "your_api_key_here":
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def generate_structured_json(
        self, 
        prompt: str, 
        response_schema: Any, 
        model_name: str = "gemini-3.5-flash-lite"
    ) -> Dict[str, Any]:
        """
        Generate structured JSON using Gemini API.
        """
        if not self.client:
            logger.warning("AI_API_KEY is not configured or is default. Returning mock response.")
            return self._get_mock_response(response_schema)
            
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
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
