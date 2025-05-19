import logging
import sys
from typing import Optional, Dict


def get_logger(context: Optional[Dict[str, str]] = None) -> logging.Logger:
    logger = logging.getLogger()
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)s [%(context)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.context = " ".join([f"{k}={v}" for k, v in (context or {}).items()])
            return True

    logger.filters.clear()
    logger.addFilter(ContextFilter())
    return logger
