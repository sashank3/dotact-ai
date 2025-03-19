import os
import logging
import sys
from datetime import datetime
from .app_dirs import APP_DIRS, IS_FROZEN

def configure_logging():
    """
    Configure minimal initial logging and prepare directories for log_manager.
    
    This is just the initial setup - the full logging configuration
    will be handled by log_manager with session directories.
    """
    # Create logs base directory
    logs_dir = APP_DIRS['logs_dir']
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a timestamp-based session directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(logs_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Set environment variable for session directory (for subprocesses)
    os.environ["SESSION_DIR"] = session_dir
    
    # Setup minimal console logging until log_manager takes over
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # Add a simple console handler for initial logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Log basic info about the environment
    logging.info(f"Initial setup - Logs directory: {logs_dir}")
    logging.info(f"Session directory: {session_dir}")
    if IS_FROZEN:
        logging.info("Running as packaged application")
    else:
        logging.info("Running in development mode")
    
    # Return paths for log_manager to use
    return {
        'logs_dir': logs_dir,
        'session_dir': session_dir
    } 