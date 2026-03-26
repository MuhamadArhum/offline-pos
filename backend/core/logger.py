
import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure Logging
logger = logging.getLogger("POS_App")
logger.setLevel(logging.INFO)

# File Handler (Rotating)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=5*1024*1024, # 5 MB
    backupCount=5,
    encoding="utf-8"
)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)

# Console Handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name=None):
    if name:
        return logging.getLogger(f"POS_App.{name}")
    return logger

def setup_logger():
    """Compatibility wrapper for main.py"""
    return logger
