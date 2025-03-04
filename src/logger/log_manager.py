"""Manages logging setup and directory structure"""
import os
import logging
import sys
from datetime import datetime
from src.global_config import LOGGING_CONFIG

class LogManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        if "SESSION_DIR" in os.environ:
            self.session_dir = os.environ["SESSION_DIR"]
            # Re-initialize file paths from existing session dir
            self.log_file = os.path.join(self.session_dir, "app.log")
            self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
        else:
            # Only create new session dir if not already set
            base_logs_dir = LOGGING_CONFIG["logs_dir"]
            os.makedirs(base_logs_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(base_logs_dir, f"session_{timestamp}")
            os.makedirs(self.session_dir, exist_ok=True)
            
            self.log_file = os.path.join(self.session_dir, "app.log")
            self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
            
            os.environ["SESSION_DIR"] = self.session_dir  # Set for child processes
        
        # Configure logging - always do this regardless of whether session dir already exists
        self._configure_logging()
        
        logging.info(f"[LOG MANAGER] Session directory: {self.session_dir}")

    def _configure_logging(self):
        # Clear existing handlers to prevent duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Configure unified logging
        formatter = logging.Formatter(LOGGING_CONFIG["format"])
        
        # Single file handler for all logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        
        # Console handler - enforce output to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(LOGGING_CONFIG["level"])
        
        # Force DEBUG level for specific modules
        logging.getLogger('src.cloud.api').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.chainlit_app').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.auth').setLevel(logging.DEBUG)

    def get_chat_history_path(self) -> str:
        return self.chat_history_file
        
    # Add a method to force reconfiguration - useful for subprocesses
    def reconfigure(self):
        self._configure_logging()
        logging.info("Logging reconfigured")

log_manager = LogManager()