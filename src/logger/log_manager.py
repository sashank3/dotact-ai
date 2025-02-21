"""Manages logging setup and directory structure"""
import os
import logging
from datetime import datetime
from src.global_config import LOGGING_CONFIG

class LogManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize log directories and paths"""
        # Get base logs directory from config and ensure it exists
        base_logs_dir = LOGGING_CONFIG["logs_dir"]
        os.makedirs(base_logs_dir, exist_ok=True)
        
        # Create timestamp-based session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(base_logs_dir, f"session_{timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Set up paths
        self.log_file = os.path.join(self.session_dir, "app.log")
        self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
        
        # Configure logging using format from config
        logging.basicConfig(
            level=LOGGING_CONFIG["level"],
            format=LOGGING_CONFIG["format"],
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
        logging.info(f"[LOG MANAGER] Initialized logging for session: {timestamp}")
        logging.info(f"[LOG MANAGER] Log file: {self.log_file}")
        logging.info(f"[LOG MANAGER] Chat history file: {self.chat_history_file}")

    def get_chat_history_path(self) -> str:
        """Get path to chat history file for current session"""
        return self.chat_history_file

# Global instance
log_manager = LogManager() 