import json
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_PATH = Path.home() / ".tenrix" / "config.json"

DEFAULT_CONFIG = {
    "active_provider": "gemini",
    "active_model": {
        "gemini":     "gemini-2.5-flash",
        "openai":     "gpt-4o-mini",
        "groq":       "llama3-8b-8192",
        "openrouter": "mistralai/mistral-7b-instruct",
        "ollama":     "llama3",
    },
    "ollama_base_url":         "http://localhost:11434",
    "interpretation_language": "English",
    "last_file":               None,
}


def load_config() -> dict:
    """Load config from file. Returns DEFAULT_CONFIG if file not found."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = {**DEFAULT_CONFIG, **saved}
            if "active_model" in saved and isinstance(saved["active_model"], dict):
                merged["active_model"] = {**DEFAULT_CONFIG["active_model"], **saved["active_model"]}
            return merged
        return dict(DEFAULT_CONFIG)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Save config to file."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


_config_cache = None


def _get_config() -> dict:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache


def _save() -> None:
    save_config(_get_config())


def get(key: str, default=None):
    """Get a config value."""
    return _get_config().get(key, default)


def set(key: str, value) -> None:
    """Set a config value and persist."""
    _get_config()[key] = value
    _save()


def get_active_provider() -> str:
    return _get_config().get("active_provider", "gemini")


def set_active_provider(provider: str) -> None:
    _get_config()["active_provider"] = provider
    _save()


def get_active_model() -> str:
    provider = get_active_provider()
    models = _get_config().get("active_model", {})
    return models.get(provider, DEFAULT_CONFIG["active_model"].get(provider, ""))


def set_active_model(model: str) -> None:
    provider = get_active_provider()
    if "active_model" not in _get_config():
        _get_config()["active_model"] = dict(DEFAULT_CONFIG["active_model"])
    _get_config()["active_model"][provider] = model
    _save()


def get_language() -> str:
    return _get_config().get("interpretation_language", "English")


def set_language(lang: str) -> None:
    _get_config()["interpretation_language"] = lang
    _save()


def get_ollama_base_url() -> str:
    return _get_config().get("ollama_base_url", "http://localhost:11434")
