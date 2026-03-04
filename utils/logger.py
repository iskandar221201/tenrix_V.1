import logging
from pathlib import Path

LOG_PATH = Path.home() / ".tenrix" / "tenrix.log"


def get_logger(name: str) -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
