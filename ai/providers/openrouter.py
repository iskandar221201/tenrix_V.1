from ai.base_provider import AIProvider, AIProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterProvider(AIProvider):
    BASE_URL = "https://openrouter.ai/api/v1"

    @property
    def requires_api_key(self) -> bool:
        return True

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        try:
            import httpx
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = httpx.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "messages": messages, **kwargs},
                timeout=60.0,
            )
            if response.status_code == 429:
                raise AIProviderError(
                    message="Rate limited", provider="openrouter", retryable=True
                )
            if response.status_code in (401, 403):
                raise AIProviderError(
                    message=f"Auth error: {response.status_code}",
                    provider="openrouter", retryable=False,
                )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                message=str(e), provider="openrouter", retryable=False
            )

    def validate_key(self) -> bool:
        try:
            import httpx
            response = httpx.get(
                f"{self.BASE_URL}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter key validation failed: {e}")
            return False
