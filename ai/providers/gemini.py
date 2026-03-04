from ai.base_provider import AIProvider, AIProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(AIProvider):
    @property
    def requires_api_key(self) -> bool:
        return True

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        """Return response text. Raise AIProviderError on failure."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system if system else None,
            )
            # Handle json_mode if provided in kwargs
            # Handle max_tokens if provided in kwargs
            # (Actual implementation-specific logic would go here, but for now we just accept them)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            retryable = "429" in str(e) or "resource exhausted" in err_str or "quota" in err_str
            raise AIProviderError(
                message=str(e), provider="gemini", retryable=retryable
            )

    def validate_key(self) -> bool:
        """Test if key is valid. Return True/False. Never raise."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            model.generate_content("test")
            return True
        except Exception as e:
            logger.error(f"Gemini key validation failed: {e}")
            return False
