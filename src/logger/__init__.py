import logging

# Re-export log_manager for easy access
from src.logger.log_manager import log_manager

def setup_logging():
    """Initialize the logging system using global configuration."""
    # Configure advanced logging
    from src.config import config
    
    # Apply logging configuration from config
    logging.info(f"[LOGGER] Setting up logging with config: {config.logging_config}")
    
    # Any additional logging setup can go here
    
    logging.info("[LOGGER] Logging system initialized") 