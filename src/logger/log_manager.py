"""Manages logging setup and directory structure"""
import os
import logging
import sys
import queue
import threading
from datetime import datetime
from logging.handlers import QueueHandler, QueueListener
from src.config import config
from src.bootstrap import is_frozen


# --- Configuration ---
LOG_FORMAT = config.logging_config.get("format", "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
ROOT_LOG_LEVEL = logging.DEBUG # Let root logger capture everything
CONSOLE_LOG_LEVEL = config.logging_config.get("level", logging.INFO) # Console level
FILE_LOG_LEVEL = logging.DEBUG # File level - capture everything in files
ERROR_LOG_LEVEL = logging.WARNING # Error file level

class LogManager:
    _instance = None
    _lock = threading.Lock() # Lock for thread-safe singleton creation

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Use a flag to prevent recursive initialization if logging is used *during* init
                    cls._instance._initialized = False
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Prevent re-initialization within the same process
        if hasattr(self, '_initialized') and self._initialized:
            print(f"[LogManager._initialize {os.getpid()}] Already initialized. Skipping.", file=sys.stderr)
            return

        print(f"[LogManager._initialize {os.getpid()}] Initializing...", file=sys.stderr)

        # Determine Session Directory (Crucial for subprocesses)
        if "SESSION_DIR" in os.environ:
            self.session_dir = os.environ["SESSION_DIR"]
            print(f"[LogManager._initialize {os.getpid()}] Using existing SESSION_DIR: {self.session_dir}", file=sys.stderr)
        else:
            # Only create new session dir if not already set (likely the parent process)
            base_logs_dir = config.logging_config["logs_dir"]
            os.makedirs(base_logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(base_logs_dir, f"session_{timestamp}")
            os.makedirs(self.session_dir, exist_ok=True)
            # Set environment variable for potential child processes *before* configuring logging
            os.environ["SESSION_DIR"] = self.session_dir
            print(f"[LogManager._initialize {os.getpid()}] Created new SESSION_DIR: {self.session_dir}", file=sys.stderr)

        # Define log file paths based on the session directory
        self.keenmind_log_file = os.path.join(self.session_dir, "keenplay.log")
        self.error_log_file = os.path.join(self.session_dir, "error.log")
        self.chat_history_file = os.path.join(self.session_dir, "chat_history.json")

        # Shared log queue for this process
        self.log_queue = queue.Queue(-1)
        self.queue_listener = None # Initialize listener attribute

        # Configure logging handlers and listener for *this* process
        self._configure_logging()

        # Mark as initialized for this process
        self._initialized = True
        print(f"[LogManager._initialize {os.getpid()}] Initialization complete. Logging configured.", file=sys.stderr)
        # Use try-except for initial log message in case configuration failed silently
        try:
            logging.info(f"[LOG MANAGER {os.getpid()}] Session directory: {self.session_dir}")
            logging.debug(f"[LOG MANAGER {os.getpid()}] Python executable: {sys.executable}")
            logging.debug(f"[LOG MANAGER {os.getpid()}] Frozen: {is_frozen()}")
        except Exception as log_init_err:
             print(f"[LogManager._initialize {os.getpid()}] Error during initial logging message: {log_init_err}", file=sys.stderr)


    def _configure_logging(self):
        """Sets up logging handlers and listener for the current process."""
        process_id = os.getpid()
        print(f"[LogManager._configure_logging {process_id}] Configuring logging...", file=sys.stderr)

        # --- Stop existing listener if any ---
        if hasattr(self, 'queue_listener') and self.queue_listener:
            print(f"[LogManager._configure_logging {process_id}] Stopping existing queue listener...", file=sys.stderr)
            try:
                self.queue_listener.stop()
                print(f"[LogManager._configure_logging {process_id}] Existing queue listener stopped.", file=sys.stderr)
            except Exception as e:
                print(f"[LogManager._configure_logging {process_id}] Error stopping existing listener: {e}", file=sys.stderr)
            self.queue_listener = None # Reset attribute

        # --- Clear existing handlers from root logger ---
        root_logger = logging.getLogger()
        print(f"[LogManager._configure_logging {process_id}] Current root handlers before removal: {root_logger.handlers}", file=sys.stderr)
        if root_logger.hasHandlers():
             for handler in root_logger.handlers[:]:
                 print(f"[LogManager._configure_logging {process_id}] Removing handler: {handler}", file=sys.stderr)
                 root_logger.removeHandler(handler)
                 try:
                     handler.close()
                 except Exception as close_err:
                     print(f"[LogManager._configure_logging {process_id}] Ignored error closing handler {handler}: {close_err}", file=sys.stderr)
        print(f"[LogManager._configure_logging {process_id}] Handlers after removal: {root_logger.handlers}", file=sys.stderr)

        # --- Create formatter ---
        formatter = logging.Formatter(LOG_FORMAT)

        # --- Create handlers for the listener ---
        handlers_for_listener = []

        # 1. Main file handler (keenplay.log)
        try:
            main_file_handler = logging.FileHandler(self.keenmind_log_file, mode='a', encoding='utf-8', errors='ignore')
            main_file_handler.setFormatter(formatter)
            main_file_handler.setLevel(FILE_LOG_LEVEL)
            handlers_for_listener.append(main_file_handler)
            print(f"[LogManager._configure_logging {process_id}] Added main_file_handler for {self.keenmind_log_file}", file=sys.stderr)
        except Exception as e:
            print(f"[LogManager._configure_logging {process_id}] Error creating main log file handler: {e}", file=sys.stderr)
            # Optionally re-raise or handle more gracefully depending on requirements
            # raise e

        # 2. Error file handler (error.log)
        try:
            error_file_handler = logging.FileHandler(self.error_log_file, mode='a', encoding='utf-8', errors='ignore')
            error_file_handler.setFormatter(formatter)
            error_file_handler.setLevel(ERROR_LOG_LEVEL)
            handlers_for_listener.append(error_file_handler)
            print(f"[LogManager._configure_logging {process_id}] Added error_file_handler for {self.error_log_file}", file=sys.stderr)
        except Exception as e:
            print(f"[LogManager._configure_logging {process_id}] Error creating error log file handler: {e}", file=sys.stderr)
            # Optionally re-raise or handle

        # 3. Console handler (only if not frozen/packaged and stdout is a tty)
        if not is_frozen():
            try:
                if sys.stdout and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
                    console_handler = logging.StreamHandler(sys.stdout)
                    console_handler.setFormatter(formatter)
                    console_handler.setLevel(CONSOLE_LOG_LEVEL)
                    handlers_for_listener.append(console_handler)
                    print(f"[LogManager._configure_logging {process_id}] Added console handler (dev mode).", file=sys.stderr)
                else:
                    print(f"[LogManager._configure_logging {process_id}] Skipping console handler (stdout not a tty or None/unavailable).", file=sys.stderr)
            except Exception as e:
                print(f"[LogManager._configure_logging {process_id}] Error creating console handler: {e}", file=sys.stderr)
        else:
             print(f"[LogManager._configure_logging {process_id}] Skipping console handler (frozen mode).", file=sys.stderr)

        # --- Setup QueueListener (if handlers exist) ---
        if handlers_for_listener:
            if not hasattr(self, 'log_queue') or self.log_queue is None:
                 self.log_queue = queue.Queue(-1)
                 print(f"[LogManager._configure_logging {process_id}] Recreated log_queue.", file=sys.stderr)

            self.queue_listener = QueueListener(
                self.log_queue,
                *handlers_for_listener,
                respect_handler_level=True
            )
            print(f"[LogManager._configure_logging {process_id}] Created QueueListener with handlers: {handlers_for_listener}", file=sys.stderr)
        else:
            # If NO handlers could be created, logging won't work. This is critical.
            print(f"[LogManager._configure_logging {process_id}] CRITICAL: No valid handlers created for QueueListener! Logging will likely fail.", file=sys.stderr)
            self.queue_listener = None
            # Consider raising an exception here if logging is absolutely essential
            # raise RuntimeError("Failed to initialize any logging handlers.")

        # --- Setup QueueHandler (attached to root logger) ---
        if not hasattr(self, 'log_queue') or self.log_queue is None:
             self.log_queue = queue.Queue(-1)
             print(f"[LogManager._configure_logging {process_id}] Recreated log_queue before QueueHandler.", file=sys.stderr)

        queue_handler = QueueHandler(self.log_queue)
        root_logger.addHandler(queue_handler)
        print(f"[LogManager._configure_logging {process_id}] Added QueueHandler to root logger.", file=sys.stderr)

        # --- Configure root logger level ---
        root_logger.setLevel(ROOT_LOG_LEVEL)
        print(f"[LogManager._configure_logging {process_id}] Set root logger level to {logging.getLevelName(ROOT_LOG_LEVEL)}.", file=sys.stderr)

        # --- Set specific module levels (optional, but good practice) ---
        logging.getLogger('src.cloud.api').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.chainlit_app').setLevel(logging.DEBUG)
        logging.getLogger('src.ui.auth').setLevel(logging.DEBUG)
        logging.getLogger('src.gsi.server').setLevel(logging.INFO)
        logging.getLogger('src.gsi.state_manager').setLevel(logging.INFO)
        logging.getLogger('uvicorn').setLevel(logging.INFO)
        logging.getLogger('uvicorn.error').setLevel(logging.INFO)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.INFO)
        logging.getLogger('botocore').setLevel(logging.INFO)
        logging.getLogger('urllib3').setLevel(logging.INFO)
        # Add chainlit specific logger level if needed/known
        # logging.getLogger('chainlit').setLevel(logging.INFO)

        # --- Start the QueueListener thread ---
        if self.queue_listener:
            print(f"[LogManager._configure_logging {process_id}] Starting QueueListener thread...", file=sys.stderr)
            try:
                self.queue_listener.start()
                print(f"[LogManager._configure_logging {process_id}] QueueListener started.", file=sys.stderr)
            except Exception as start_err:
                 print(f"[LogManager._configure_logging {process_id}] FAILED to start QueueListener thread: {start_err}", file=sys.stderr)
                 self.queue_listener = None # Mark as not started
                 # Depending on requirements, might want to raise an error here too
                 # raise RuntimeError(f"Failed to start QueueListener thread: {start_err}") from start_err
        else:
            # This case implies no handlers were created earlier.
            print(f"[LogManager._configure_logging {process_id}] QueueListener not created or not started (likely no handlers).", file=sys.stderr)


        print(f"[LogManager._configure_logging {process_id}] Configuration finished.", file=sys.stderr)

    def get_chat_history_path(self) -> str:
        """Returns the path to the chat history file for the current session."""
        # Remove fallback logic - Assume initialized correctly if this method is called
        if not hasattr(self, '_initialized') or not self._initialized or not hasattr(self, 'chat_history_file'):
             # This condition indicates a programming error if called before/without init
             print(f"[LogManager {os.getpid()}] FATAL: get_chat_history_path called incorrectly (not initialized or chat_history_file missing).", file=sys.stderr)
             # Raise an error or return a clearly invalid path
             raise RuntimeError("LogManager not properly initialized before get_chat_history_path call.")
             # OR return None # Depending on how callers handle it
        return self.chat_history_file

    def shutdown_listener(self, listener, process_id):
        """Safely stops a specific QueueListener instance. Called explicitly by shutdown logic."""
        if listener:
            print(f"[LogManager.shutdown_listener {process_id}] Stopping listener {id(listener)} explicitly...", file=sys.stderr)
            try:
                listener.stop() # This should wait for the queue to empty
                print(f"[LogManager.shutdown_listener {process_id}] Listener stopped.", file=sys.stderr)
            except Exception as e:
                print(f"[LogManager.shutdown_listener {process_id}] Error stopping listener: {e}", file=sys.stderr)
        else:
             print(f"[LogManager.shutdown_listener {process_id}] No valid listener object provided to shutdown.", file=sys.stderr)

# --- Instantiate the Singleton ---
log_manager = LogManager()