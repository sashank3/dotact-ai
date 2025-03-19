"""Manages logging setup and directory structure"""
import os
import logging
import sys
import queue
from datetime import datetime
from functools import wraps
from logging.handlers import QueueHandler, QueueListener
from src.global_config import LOGGING_CONFIG
from src.exe.app_dirs import APP_DIRS, IS_FROZEN

class LogManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Get the base logs directory from APP_DIRS
        logs_dir = APP_DIRS['logs_dir']
        
        # Check if session directory already exists in environment
        if "SESSION_DIR" in os.environ:
            self.session_dir = os.environ["SESSION_DIR"]
        else:
            # Create a new session directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(logs_dir, f"session_{timestamp}")
            os.makedirs(self.session_dir, exist_ok=True)
            os.environ["SESSION_DIR"] = self.session_dir  # Set for child processes
        
        # Set up log file paths within the session directory
        self.app_log_file = os.path.join(self.session_dir, "app.log")
        self.debug_log_file = os.path.join(self.session_dir, "debug.log")
        self.error_log_file = os.path.join(self.session_dir, "error.log")  # Renamed from keenmind.log
        self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
        
        # Configure logging
        self._configure_logging()
        
        logging.info(f"[LOG MANAGER] Session directory: {self.session_dir}")

    def _configure_logging(self):
        # Clear existing handlers to prevent duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create log formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s (%(filename)s:%(lineno)d)',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create a log queue for async-safe logging
        self.log_queue = queue.Queue(-1)  # No limit on size
        
        # Create INFO-only filter
        class InfoFilter(logging.Filter):
            def filter(self, record):
                return record.levelno == logging.INFO
        
        # Create WARNING-and-above filter
        class WarningErrorFilter(logging.Filter):
            def filter(self, record):
                return record.levelno >= logging.WARNING
        
        # 1. Debug handler gets everything (DEBUG and above)
        debug_handler = logging.FileHandler(self.debug_log_file)
        debug_handler.setFormatter(detailed_formatter)
        debug_handler.setLevel(logging.DEBUG)
        
        # 2. App handler gets INFO-only logs (filtered)
        app_handler = logging.FileHandler(self.app_log_file)
        app_handler.setFormatter(simple_formatter)
        app_handler.setLevel(logging.INFO)
        app_handler.addFilter(InfoFilter())
        
        # 3. Error handler gets WARNING and ERROR logs
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setFormatter(simple_formatter)
        error_handler.setLevel(logging.WARNING)
        
        # Console handler gets INFO and above
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Setup the queue listener (runs in a separate thread)
        self.queue_listener = QueueListener(
            self.log_queue, 
            app_handler,
            debug_handler,
            error_handler,
            console_handler,
            respect_handler_level=True
        )
        
        # Setup the queue handler (used by loggers)
        queue_handler = QueueHandler(self.log_queue)
        
        # Configure the root logger
        root_logger.addHandler(queue_handler)
        root_logger.setLevel(logging.DEBUG)  # Capture all logs at the root logger
        
        # Set specific module log levels
        logging.getLogger('src.cloud.api').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.chainlit_app').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.auth').setLevel(logging.DEBUG)
        
        # Start the queue listener in a background thread
        self.queue_listener.start()
        
        # Override standard logging debug/info/warning/error methods with safe versions
        self._patch_logging_methods()

    def _patch_logging_methods(self):
        """
        Patch standard logging methods to make them safe for large objects
        and prevent event loop blocking.
        """
        # Create decorator for safe logging
        def safe_log_decorator(func):
            @wraps(func)
            def wrapper(self, msg, *args, **kwargs):
                # Convert large objects to safe representations
                if args and len(args) > 0:
                    new_args = []
                    for arg in args:
                        # If the argument is a dictionary or other large object, limit its size
                        if isinstance(arg, dict) and len(str(arg)) > 1000:
                            # Create a truncated version for large dictionaries
                            truncated = {k: str(v)[:100] + '...' if isinstance(v, str) and len(str(v)) > 100 else v 
                                        for k, v in list(arg.items())[:10]}
                            if len(arg) > 10:
                                truncated['...'] = f'[{len(arg) - 10} more items]'
                            new_args.append(truncated)
                        elif isinstance(arg, str) and len(arg) > 1000:
                            new_args.append(arg[:1000] + '... [truncated]')
                        else:
                            new_args.append(arg)
                    return func(self, msg, *new_args, **kwargs)
                return func(self, msg, *args, **kwargs)
            return wrapper
        
        # Apply the decorator to standard logging methods
        logging.Logger.debug = safe_log_decorator(logging.Logger.debug)
        logging.Logger.info = safe_log_decorator(logging.Logger.info)
        logging.Logger.warning = safe_log_decorator(logging.Logger.warning)
        logging.Logger.error = safe_log_decorator(logging.Logger.error)

    def get_chat_history_path(self) -> str:
        return self.chat_history_file
        
    def reconfigure(self):
        """Force reconfiguration of logging - useful for subprocesses"""
        # Stop any existing queue listener
        if hasattr(self, 'queue_listener') and self.queue_listener:
            self.queue_listener.stop()
            
        self._configure_logging()
        logging.info("Logging reconfigured")
    
    def shutdown(self):
        """Properly shut down logging system"""
        if hasattr(self, 'queue_listener') and self.queue_listener:
            self.queue_listener.stop()
            logging.info("Log queue listener shut down")

log_manager = LogManager()

# Ensure the log manager is properly shut down on program exit
import atexit
atexit.register(log_manager.shutdown)