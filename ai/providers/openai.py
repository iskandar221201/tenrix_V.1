from ai.base_provider import AIProvider, AIProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    @property
    def requires_api_key(self) -> bool:
        return True

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            # Map json_mode to response_format for OpenAI
            if kwargs.get("json_mode"):
                kwargs["response_format"] = {"type": "json_object"}
            
            # Clean up kwargs that complete() expects but API doesn't know
            kwargs.pop("json_mode", None)

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
                message=str(e), provider="openai", retryable=retryable
            )

    def validate_key(self) -> bool:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI key validation failed: {e}")
            return False
