# src/utils/__init__.py
import os
import sys
import asyncio
import concurrent.futures
import logging
import threading
import time
import signal

# Get a logger instance for utility functions
logger = logging.getLogger(__name__) # Use __name__ for module logger

# Re-export paths functions for easy access throughout the app
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

def setup_event_loop_policy():
    """Configure the event loop policy for better async behavior."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    loop = asyncio.new_event_loop()

    loop.set_default_executor(
        concurrent.futures.ThreadPoolExecutor(max_workers=min(32, os.cpu_count() + 4))
    )

    asyncio.set_event_loop(loop)

    logger.info("[UTILS] Configured event loop policy")
    return loop

def initiate_shutdown(
    shutdown_event: threading.Event,
    gsi_thread: threading.Thread,
    auth_thread: threading.Thread,
    gsi_server_instance, # Type hint could be uvicorn.Server if imported, but keep flexible
    auth_server_instance, # Type hint could be uvicorn.Server if imported, but keep flexible
    log_manager_instance, # Pass the log_manager instance
    signum=None
):
    """Gracefully shuts down all application components."""
    # Use logger from this module
    shutdown_logger = logging.getLogger(__name__)

    if shutdown_event.is_set():
        return # Avoid running shutdown multiple times

    if signum:
         # Use signal.Signals(signum).name if Python 3.8+
         signal_name = getattr(signal, f'SIG{signal.Signals(signum).name}', f'Signal {signum}')
         shutdown_logger.info(f"Received signal {signal_name}. Initiating graceful shutdown...")
    else:
         shutdown_logger.info("Initiating graceful shutdown...")

    shutdown_event.set()

    # No globals needed here, use passed arguments
    auth_stopped = False
    gsi_stopped = False

    if auth_server_instance:
        shutdown_logger.info("Signaling Auth Server (Uvicorn) to shut down...")
        auth_server_instance.should_exit = True
        auth_stopped = True
    else:
        shutdown_logger.warning("Auth server instance not found. Cannot signal Uvicorn directly.")

    if gsi_server_instance:
        shutdown_logger.info("Signaling GSI Server (Uvicorn) to shut down...")
        gsi_server_instance.should_exit = True
        gsi_stopped = True
    else:
        shutdown_logger.warning("GSI server instance not found. Cannot signal Uvicorn directly.")

    shutdown_logger.info("Waiting for server threads to join...")
    start_time = time.time()
    timeout = 15 # seconds

    # Check threads passed as arguments
    if auth_thread and (auth_stopped or not auth_server_instance) and auth_thread.is_alive():
        auth_thread.join(timeout=timeout)
        if auth_thread.is_alive():
            shutdown_logger.warning(f"Auth thread did not join within {timeout}s.")
        else:
            shutdown_logger.info("Auth thread joined.")
            elapsed = time.time() - start_time
            timeout = max(1, timeout - elapsed)

    if gsi_thread and (gsi_stopped or not gsi_server_instance) and gsi_thread.is_alive():
        gsi_thread.join(timeout=timeout)
        if gsi_thread.is_alive():
            shutdown_logger.warning(f"GSI thread did not join within {timeout}s.")
        else:
            shutdown_logger.info("GSI thread joined.")

    shutdown_logger.info("Shutting down logging system...")
    # Use the passed log_manager instance
    if hasattr(log_manager_instance, 'shutdown_listener') and hasattr(log_manager_instance, 'queue_listener') and log_manager_instance.queue_listener is not None:
        try:
            log_manager_instance.shutdown_listener(log_manager_instance.queue_listener, os.getpid())
        except Exception as log_shutdown_err:
            # Use print as logger might be shutting down
            print(f"Error shutting down log listener: {log_shutdown_err}", file=sys.stderr)
    elif hasattr(log_manager_instance, 'shutdown'):
         try:
             log_manager_instance.shutdown()
         except Exception as log_shutdown_err:
             print(f"Error calling log_manager.shutdown(): {log_shutdown_err}", file=sys.stderr)
    else:
        print("Could not find suitable shutdown method on log_manager.", file=sys.stderr)

    print("Graceful shutdown process finished.") # Use print as final message