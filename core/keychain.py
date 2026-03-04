import keyring
from utils.logger import get_logger

logger = get_logger(__name__)
SERVICE = "tenrix"
MAX_KEYS = 20


def save_key(provider: str, key: str, index: int) -> bool:
    """Save to OS Keychain. Returns True on success. Never raises."""
    try:
        username = f"{provider}/{index}"
        keyring.set_password(SERVICE, username, key)
        logger.info(f"Key saved for provider={provider} index={index}")
        return True
    except Exception as e:
        logger.error(f"Failed to save key for provider={provider} index={index}: {e}")
        return False


def get_key(provider: str, index: int) -> str | None:
    """Get from OS Keychain. Returns None if not found. Never raises."""
    try:
        username = f"{provider}/{index}"
        return keyring.get_password(SERVICE, username)
    except Exception as e:
        logger.error(f"Failed to get key for provider={provider} index={index}: {e}")
        return None


def get_all_keys(provider: str) -> list[str]:
    """Get all stored keys for provider. Returns empty list if none."""
    keys = []
    for i in range(MAX_KEYS):
        k = get_key(provider, i)
        if k is not None:
            keys.append(k)
    return keys


def delete_key(provider: str, index: int) -> bool:
    """Delete a key. Returns True on success."""
    try:
        username = f"{provider}/{index}"
        keyring.delete_password(SERVICE, username)
        logger.info(f"Key deleted for provider={provider} index={index}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete key for provider={provider} index={index}: {e}")
        return False


def count_keys(provider: str) -> int:
    """Count stored keys for provider."""
    return len(get_all_keys(provider))
