"""
Logging utility for the SDK.
"""
import logging

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger."""
    logger = logging.getLogger(name)
    return logger
