import logging
import google.generativeai as genai
from app.core.config import settings
from typing import Optional

logger = logging.getLogger("Veridian.LLM")

class LLMEngine:
    def __init__(self):
        self.model = None
        try:
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("LLM Engine initialized with Gemini API")
            else:
                logger.warning("GEMINI_API_KEY not set. LLM Engine disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")

    def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        if not self.model:
            return None
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

# Global instance
llm_engine = LLMEngine()
