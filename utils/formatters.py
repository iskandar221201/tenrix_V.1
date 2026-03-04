# utils/formatters.py
"""Formatting utility helpers."""


def format_number(value, decimals: int = 2) -> str:
    """Format a number with commas and decimal places."""
    try:
        if isinstance(value, int):
            return f"{value:,}"
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate string with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
