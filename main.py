import traceback
import threading
import time
import signal
import logging
import os
import sys

from src.bootstrap import is_frozen, get_application_root
from src.logger.log_manager import log_manager
from src.utils.shutdown import terminate_application
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

logger = logging.getLogger(__name__)

logger.info(f"Starting application in {'production' if is_frozen() else 'development'} mode")
logger.info(f"Application root: {get_application_root()}")

logger.info(f"Config path: {get_config_path()}")
logger.info(f"User data path: {get_user_data_path()}")
logger.info(f"Logs path: {get_logs_path()}")

# --- Global Shutdown Signal & Handles ---
shutdown_event = threading.Event()
chainlit_process_handle = None
gsi_thread = None
auth_thread = None

# --- Simplified Signal Handler ---
def handle_signal(signum, frame):
    """Sets the shutdown event when a signal is received."""
    if shutdown_event.is_set():
        return
    logger.warning(f"Received signal {signum}. Signaling shutdown...")
    shutdown_event.set()

def main():
    """
    Main application entry point. Sets up environment, starts services,
    waits for shutdown signal, and calls termination utility.
    """
    # Make globals modifiable
    global chainlit_process_handle, gsi_thread, auth_thread

    os.environ['MAIN_APP_PID'] = str(os.getpid())
    logger.debug(f"Main process PID: {os.getpid()} set in environment.")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    logger.info("Registered signal handlers for SIGINT and SIGTERM.")

    try:
        # --- Environment Setup ---
        from src.utils import setup_event_loop_policy
        loop = setup_event_loop_policy()

        from src.cloud import setup_api_configuration
        api_url = setup_api_configuration()
        logger.info(f"API URL configured: {api_url}")

        from src.gsi import setup_gsi_files
        setup_gsi_files()

        # --- Start Services ---
        from src.gsi import start_gsi_server
        from src.ui import start_auth_server
        from src.ui import auth as auth_module

        gsi_thread = start_gsi_server()
        auth_thread = start_auth_server()

        if not gsi_thread or not auth_thread:
             logger.error("Failed to start GSI or Auth thread. Exiting.")
             # Attempt partial cleanup if desired, otherwise exit
             sys.exit(1) # Exit if essential threads didn't start

        # --- Retrieve Chainlit Process Handle ---
        time.sleep(30)
        chainlit_process_handle = getattr(auth_module, 'chainlit_process', None)
        if chainlit_process_handle:
             logger.info(f"Retrieved Chainlit process handle (PID: {chainlit_process_handle.pid}).")
        else:
             logger.warning("Could not retrieve Chainlit process handle after startup.")


        # --- Wait for Shutdown Signal ---
        logger.info("All services started. Waiting for shutdown signal...")
        shutdown_event.wait() # Block until event is set
        logger.info("Shutdown signal received by main thread.")

        # --- Call Termination Function ---
        # Pass only the required handles
        terminate_application(
            shutdown_event=shutdown_event,
            chainlit_process_handle=chainlit_process_handle,
            gsi_thread=gsi_thread,
            auth_thread=auth_thread
        )

    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught directly in main. Initiating shutdown...")
        if not shutdown_event.is_set():
             shutdown_event.set()
        terminate_application(shutdown_event, chainlit_process_handle, gsi_thread, auth_thread)
    except Exception as e:
        logger.error(f"Unhandled error in main function: {str(e)}")
        logger.error(traceback.format_exc())
        logger.info("Attempting emergency cleanup...")
        if not shutdown_event.is_set():
             shutdown_event.set()
        terminate_application(shutdown_event, chainlit_process_handle, gsi_thread, auth_thread)

    logger.info("Application main function finished unexpectedly.")


if __name__ == "__main__":
    main()