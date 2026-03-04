from ai.base_provider import AIProvider, AIProviderError
from core.config import get_ollama_base_url
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(AIProvider):
    @property
    def requires_api_key(self) -> bool:
        return False

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        try:
            import httpx
            base_url = get_ollama_base_url()
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system
            
            # Merge kwargs into the payload, allowing kwargs to override existing keys
            payload.update(kwargs)

            response = httpx.post(
                f"{base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            if response.status_code == 429:
                raise AIProviderError(
                    message="Rate limited", provider="ollama", retryable=True
                )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                message=str(e), provider="ollama", retryable=False
            )

    def validate_key(self) -> bool:
        try:
            import httpx
            base_url = get_ollama_base_url()
            response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama validation failed: {e}")
            return False
