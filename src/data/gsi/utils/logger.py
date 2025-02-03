import logging
import os
from src.data.gsi.config.paths import LOGS_DIR


def setup_logging(log_file="gsi_module.log"):
    """
    Configures logging for the GSI module.
    :param log_file: Name of the log file where logs will be saved.
    """
    log_path = os.path.join(LOGS_DIR, log_file)

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
