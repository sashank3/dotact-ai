import logging
import os
from src.config.global_config import GLOBAL_CONFIG  # Import the new global config

# Retrieve log directory from global config
LOGS_DIR = GLOBAL_CONFIG.get("data", {}).get("gsi", {}).get("logs_dir", "logs")  # Default to "logs" if missing

# Ensure the log directory exists
os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logging(log_file="gsi_module.log"):
    """
    Configures logging for the GSI module.
    Ensures that duplicate handlers are not added.
    """
    log_path = os.path.join(LOGS_DIR, log_file)

    # Check if handlers are already set up
    if len(logging.getLogger().handlers) > 0:
        return  # Prevent duplicate handlers

    # Create handlers
    file_handler = logging.FileHandler(log_path, mode="a")
    console_handler = logging.StreamHandler()

    # Set log level and format
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    file_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Get the root logger and attach handlers
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info("Logging setup complete for GSI module.")
