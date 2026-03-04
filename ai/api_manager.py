from ai.base_provider import AIProviderError
from ai.provider_registry import get_provider, PROVIDER_META
from core.keychain import get_all_keys
from core.config import get_active_provider, get_active_model
from utils.logger import get_logger

logger = get_logger(__name__)


class AllKeysExhaustedError(Exception):
    """Raised when all keys have been rate-limited."""
    pass


class APIManager:
    def __init__(self, provider_name: str, model: str = ""):
        """Load keys from keychain automatically via core.keychain.get_all_keys()."""
        self._provider_name = provider_name
        self._model = model or PROVIDER_META.get(provider_name, {}).get("default_model", "")
        self._keys: list[str] = []
        self._current_key_index = 0
        self._provider = None
        self._load_keys()

    def _load_keys(self):
        """Load keys from keychain."""
        meta = PROVIDER_META.get(self._provider_name, {})
        if meta.get("local", False):
            # Local providers (Ollama) don't need keys
            self._keys = [""]
            self._provider = get_provider(self._provider_name, "", self._model)
        else:
            self._keys = get_all_keys(self._provider_name)
            if self._keys:
                self._current_key_index = 0
                self._provider = get_provider(
                    self._provider_name, self._keys[0], self._model
                )
            else:
                self._provider = None

    def call(self, prompt: str, system: str = "", **kwargs) -> str:
        """
        Call AI. Rotate keys automatically on rate limit (AIProviderError retryable=True).
        Raise AllKeysExhaustedError if all keys rate-limited.
        Raise AIProviderError for non-retryable errors.
        """
        if not self._provider:
            raise AllKeysExhaustedError("No API keys configured.")

        if not self._keys:
            raise AllKeysExhaustedError("No API keys available.")

        tried = set()
        while len(tried) < len(self._keys):
            try:
                return self._provider.complete(prompt, system, **kwargs)
            except AIProviderError as e:
                if e.retryable and len(self._keys) > 1:
                    tried.add(self._current_key_index)
                    self._rotate_key()
                    if self._current_key_index in tried:
                        raise AllKeysExhaustedError(
                            f"All {len(self._keys)} keys exhausted for {self._provider_name}"
                        )
                else:
                    raise

        raise AllKeysExhaustedError(
            f"All {len(self._keys)} keys exhausted for {self._provider_name}"
        )

    def _rotate_key(self):
        """Switch to the next available key."""
        if len(self._keys) <= 1:
            return
        self._current_key_index = (self._current_key_index + 1) % len(self._keys)
        self._provider = get_provider(
            self._provider_name,
            self._keys[self._current_key_index],
            self._model,
        )
        logger.info(f"Rotated to key index {self._current_key_index} for {self._provider_name}")

    def switch_provider(self, provider_name: str, model: str = "") -> None:
        """Hot-swap provider. Reloads keys from keychain."""
        self._provider_name = provider_name
        self._model = model or PROVIDER_META.get(provider_name, {}).get("default_model", "")
        self._current_key_index = 0
        self._load_keys()

    def validate_current_key(self) -> bool:
        """Validate the current key."""
        if self._provider is None:
            return False
        return self._provider.validate_key()

    def reload_keys(self) -> None:
        """Reload keys from keychain - call after user adds/removes key."""
        self._load_keys()

    def get_active_provider_name(self) -> str:
        return self._provider_name

    def get_active_model(self) -> str:
        return self._model

    def get_key_count(self) -> int:
        meta = PROVIDER_META.get(self._provider_name, {})
        if meta.get("local", False):
            return 0
        return len(self._keys)


def init_from_config() -> "APIManager | None":
    """Init from saved config + keychain. Return None if no keys found (except Ollama)."""
    provider = get_active_provider()
    model = get_active_model()
    meta = PROVIDER_META.get(provider, {})

    if meta.get("local", False):
        return APIManager(provider, model)

    keys = get_all_keys(provider)
    if not keys:
        return None

    return APIManager(provider, model)
