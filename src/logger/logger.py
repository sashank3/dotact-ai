# logger.py

import logging
import os
from src.global_config import GLOBAL_CONFIG

def setup_logging(log_file="app.log", level=logging.INFO):
    """
    Configures logging for the entire app with a single function.
    Avoids adding duplicate handlers if they're already present.
    """
    # Read logs directory from global config or default to "./logs"
    logs_dir = GLOBAL_CONFIG.get("data", {}).get("gsi", {}).get("logs_dir", "logs")

    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, log_file)

    # If a logger already has handlers, don't add them again
    if len(logging.getLogger().handlers) > 0:
        return

    # Create file + console handlers
    file_handler = logging.FileHandler(log_path, mode="a")
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info("Unified logging setup complete.")

