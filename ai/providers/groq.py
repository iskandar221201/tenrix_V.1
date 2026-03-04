from ai.base_provider import AIProvider, AIProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class GroqProvider(AIProvider):
    @property
    def requires_api_key(self) -> bool:
        return True

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        try:
            import groq
            client = groq.Groq(api_key=self.api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e).lower()
            retryable = "429" in str(e) or "rate" in err_str
            raise AIProviderError(
                message=str(e), provider="groq", retryable=retryable
            )

    def validate_key(self) -> bool:
        try:
            import groq
            client = groq.Groq(api_key=self.api_key)
            client.models.list()
            return True
        except Exception as e:
            logger.error(f"Groq key validation failed: {e}")
            return False
