"""
Logging configuration for AI Voice Customer Support Agent.
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "voice_support", level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a structured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        log_format = (
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s"
        )
        formatter = logging.Formatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))
        logger.propagate = False
    elif level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    return logger


# Default application logger
logger = setup_logger()
