import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Resolve base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "errors.log"

def get_logger(script_name):
    """
    Returns a configured logger instance that writes to a shared errors.log file
    with 5MB file rotation and custom formatting.
    """
    # Ensure logs directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers if get_logger is called multiple times
    if not logger.handlers:
        # Create RotatingFileHandler: max 5MB, keep 3 backups
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        
        # Format: 2026-06-07 09:15:32 | capture_rss.py | ERROR | <message>
        # Align level names to make logs readable
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(name)s | %(levelname)-7s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add console streaming handler to keep terminal feedback active
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger
