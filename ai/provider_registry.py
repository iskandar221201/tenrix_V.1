from ai.base_provider import AIProvider
from utils.logger import get_logger

logger = get_logger(__name__)

PROVIDER_META = {
    "gemini": {
        "label":         "Google Gemini",
        "free_tier":     True,
        "local":         False,
        "default_model": "gemini-2.5-flash",
        "models":        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        "key_prefix":    "AIza",
    },
    "openai": {
        "label":         "OpenAI",
        "free_tier":     False,
        "local":         False,
        "default_model": "gpt-4o-mini",
        "models":        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "key_prefix":    "sk-",
    },
    "groq": {
        "label":         "Groq",
        "free_tier":     True,
        "local":         False,
        "default_model": "llama3-8b-8192",
        "models":        ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"],
        "key_prefix":    "gsk_",
    },
    "openrouter": {
        "label":         "OpenRouter",
        "free_tier":     True,
        "local":         False,
        "default_model": "mistralai/mistral-7b-instruct",
        "models":        ["mistralai/mistral-7b-instruct", "meta-llama/llama-3-8b-instruct"],
        "key_prefix":    "sk-or-",
    },
    "ollama": {
        "label":         "Ollama (Local)",
        "free_tier":     True,
        "local":         True,
        "default_model": "llama3",
        "models":        [],
        "key_prefix":    None,
    },
}


def get_provider(name: str, api_key: str = "", model: str = "") -> AIProvider:
    """Instantiate provider. Raise ValueError for unknown name."""
    if name not in PROVIDER_META:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDER_META.keys())}")

    if not model:
        model = PROVIDER_META[name]["default_model"]

    if name == "gemini":
        from ai.providers.gemini import GeminiProvider
        return GeminiProvider(api_key, model)
    elif name == "openai":
        from ai.providers.openai import OpenAIProvider
        return OpenAIProvider(api_key, model)
    elif name == "groq":
        from ai.providers.groq import GroqProvider
        return GroqProvider(api_key, model)
    elif name == "openrouter":
        from ai.providers.openrouter import OpenRouterProvider
        return OpenRouterProvider(api_key, model)
    elif name == "ollama":
        from ai.providers.ollama import OllamaProvider
        return OllamaProvider(api_key, model)
    else:
        raise ValueError(f"Unknown provider: {name}")


def list_providers() -> list[str]:
    """Return all registered provider keys."""
    return list(PROVIDER_META.keys())
