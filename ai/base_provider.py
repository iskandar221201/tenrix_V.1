from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIProviderError(Exception):
    message: str
    provider: str
    retryable: bool   # True = rate limit -> rotate key. False = bad key -> raise.

    def __str__(self):
        return f"AIProviderError({self.provider}): {self.message} (retryable={self.retryable})"


class AIProvider(ABC):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        """Return response text. Raise AIProviderError on failure."""

    @abstractmethod
    def validate_key(self) -> bool:
        """Test if key is valid. Return True/False. Never raise."""

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        ...
