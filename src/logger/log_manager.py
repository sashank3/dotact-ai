"""Manages logging setup and directory structure"""
import os
import logging
import sys
import queue
from datetime import datetime
from functools import wraps
from logging.handlers import QueueHandler, QueueListener
from src.config import config
from src.bootstrap import is_frozen

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
            self.keenmind_log_file = os.path.join(self.session_dir, "keenmind.log")
            self.error_log_file = os.path.join(self.session_dir, "error.log")
            self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
        else:
            # Only create new session dir if not already set
            base_logs_dir = config.logging_config["logs_dir"]
            os.makedirs(base_logs_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(base_logs_dir, f"session_{timestamp}")
            os.makedirs(self.session_dir, exist_ok=True)
            
            self.keenmind_log_file = os.path.join(self.session_dir, "keenmind.log")
            self.error_log_file = os.path.join(self.session_dir, "error.log")
            self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")
            
            os.environ["SESSION_DIR"] = self.session_dir  # Set for child processes
        
        # Configure logging - always do this regardless of whether session dir already exists
        self._configure_logging()
        
        logging.info(f"[LOG MANAGER] Session directory: {self.session_dir}")

    def _configure_logging(self):
        # Clear existing handlers to prevent duplicates
        root_logger = logging.getLogger()
        # Stop listener if it exists before removing handlers
        if hasattr(self, 'queue_listener') and self.queue_listener:
             try:
                 self.queue_listener.stop()
             except Exception as e:
                 # Use print here as logging might be broken during reconfiguration
                 print(f"Error stopping existing queue listener: {e}", file=sys.stderr)
             self.queue_listener = None # Ensure it's reset

        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            # Attempt to close handler if possible
            try:
                handler.close()
            except Exception:
                pass # Ignore errors closing handlers

        # Create log formatter
        log_format = config.logging_config.get("format", "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
        formatter = logging.Formatter(log_format)

        # Create a log queue for async-safe logging
        if not hasattr(self, 'log_queue') or self.log_queue is None:
             self.log_queue = queue.Queue(-1) # No limit on size

        # --- Create handlers ---
        handlers_for_listener = []

        # 1. Main log file handler (keenmind.log) - logs everything
        try:
            main_file_handler = logging.FileHandler(self.keenmind_log_file, mode='a', encoding='utf-8')
            main_file_handler.setFormatter(formatter)
            main_file_handler.setLevel(config.logging_config.get("level", logging.INFO))
            handlers_for_listener.append(main_file_handler)
        except Exception as e:
            print(f"Error creating main log file handler: {e}", file=sys.stderr)


        # 2. Error log file handler (error.log) - logs warnings and errors only
        try:
            error_file_handler = logging.FileHandler(self.error_log_file, mode='a', encoding='utf-8')
            error_file_handler.setFormatter(formatter)
            error_file_handler.setLevel(logging.WARNING) # WARNING and higher (ERROR, CRITICAL)
            handlers_for_listener.append(error_file_handler)
        except Exception as e:
            print(f"Error creating error log file handler: {e}", file=sys.stderr)


        # 3. Console handler - Conditionally add only if NOT frozen (windowed)
        if not is_frozen():
            try:
                # Check if stdout is valid before creating handler
                if sys.stdout:
                    console_handler = logging.StreamHandler(sys.stdout)
                    console_handler.setFormatter(formatter)
                    console_handler.setLevel(config.logging_config.get("level", logging.INFO))
                    handlers_for_listener.append(console_handler)
                else:
                     # Use print as logging might not be fully working
                     print("[LogManager] sys.stdout is None, console handler disabled.", file=sys.stderr)
            except Exception as e:
                 print(f"Error creating console handler: {e}", file=sys.stderr)
        else:
             # Use print as logging might not be fully working
             print("[LogManager] Frozen mode detected, console handler disabled.", file=sys.stderr)


        # Setup the queue listener (runs in a separate thread)
        # Only proceed if we have valid handlers
        if handlers_for_listener:
            self.queue_listener = QueueListener(
                self.log_queue,
                *handlers_for_listener, # Pass the list of handlers
                respect_handler_level=True
            )
        else:
             print("[LogManager] No valid handlers configured for QueueListener!", file=sys.stderr)
             self.queue_listener = None # Ensure listener is None if setup failed

        # Setup the queue handler (used by loggers)
        queue_handler = QueueHandler(self.log_queue)

        # Configure the root logger
        root_logger.addHandler(queue_handler)
        root_logger.setLevel(config.logging_config.get("level", logging.INFO))

        # Set specific module log levels (Consider moving these to your config file)
        logging.getLogger('src.cloud.api').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.chainlit_app').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.auth').setLevel(logging.DEBUG)
        # Consider adjusting uvicorn levels if needed, though log_config handles its internal setup
        logging.getLogger('uvicorn').setLevel(logging.INFO)
        logging.getLogger('uvicorn.error').setLevel(logging.INFO)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING) # Keep access logs quieter at root level

        # Start the queue listener in a background thread if it was created
        if self.queue_listener:
            self.queue_listener.start()
            # Use print initially as logging might rely on the listener
            print("[LogManager] QueueListener started.")
        else:
            print("[LogManager] QueueListener not started due to handler errors.", file=sys.stderr)


        # Patching logging methods might not be necessary if QueueHandler solves blocking,
        # but keep if you handle very large objects frequently.
        # Ensure patching happens only once if _configure_logging can be called multiple times.
        if not hasattr(self, '_logging_patched') or not self._logging_patched:
             self._patch_logging_methods()
             self._logging_patched = True

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