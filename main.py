import threading
import time
import signal
import traceback

# Import bootstrap to initialize environment
from src.bootstrap import is_frozen, get_application_root

# Import the log_manager first to ensure proper logging configuration
from src.logger.log_manager import log_manager

import logging
from src.utils import initiate_shutdown, run_system_tray

# Get a logger instance for this module
logger = logging.getLogger(__name__)

logger.info(f"Starting application in {'production' if is_frozen() else 'development'} mode")
logger.info(f"Application root: {get_application_root()}")

# Import utils early to initialize path resolution
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

logger.info(f"Config path: {get_config_path()}")
logger.info(f"User data path: {get_user_data_path()}")
logger.info(f"Logs path: {get_logs_path()}")

# Global Variables for Shutdown Management - Still needed in main scope
gsi_thread = None
auth_thread = None
gsi_server_instance = None
auth_server_instance = None
shutdown_event = threading.Event()

# Wrapper function for signal handlers to pass arguments
def signal_handler_wrapper(signum, frame):
    # Call the utility function, passing the required variables from main's scope
    initiate_shutdown(
        shutdown_event=shutdown_event,
        gsi_thread=gsi_thread,
        auth_thread=auth_thread,
        gsi_server_instance=gsi_server_instance,
        auth_server_instance=auth_server_instance,
        log_manager_instance=log_manager, # Pass the imported log_manager
        signum=signum
    )

def main():
    """
    Main application entry point.
    This function coordinates all application initialization and startup.
    """
    # Use globals defined above
    global gsi_thread, auth_thread, gsi_server_instance, auth_server_instance

    # Setup Signal Handlers using the wrapper
    try: # Added try/except block for robustness
        signal.signal(signal.SIGINT, signal_handler_wrapper)
        signal.signal(signal.SIGTERM, signal_handler_wrapper)
        if hasattr(signal, 'SIGBREAK'): # Windows specific
            signal.signal(signal.SIGBREAK, signal_handler_wrapper)
        logger.info("[Main] Custom signal handlers registered.")
    except ValueError as e:
        logger.warning(f"Could not set signal handlers (maybe not in main thread?): {e}")
    except Exception as e:
        logger.error(f"Error setting signal handlers: {e}", exc_info=True)


    try:
        # Configure event loop policy
        from src.utils import setup_event_loop_policy
        loop = setup_event_loop_policy()

        # Configure API endpoints
        from src.cloud import setup_api_configuration
        api_url = setup_api_configuration()
        logger.info(f"API URL configured: {api_url}")

        # Setup GSI files if needed
        from src.gsi import setup_gsi_files
        setup_gsi_files()

        # Start services
        from src.gsi import start_gsi_server
        from src.ui import start_auth_server

        gsi_server_wrapper = []
        auth_server_wrapper = []

        logger.info("[Main] Starting GSI service...")
        gsi_thread = start_gsi_server(shutdown_event, gsi_server_wrapper)

        logger.info("[Main] Starting UI/Auth service...")
        auth_thread = start_auth_server(shutdown_event, auth_server_wrapper)

        # Capture Server Instances
        logger.info("[Main] Waiting briefly for server instances...")
        time.sleep(1) # Keep your original sleep time

        if gsi_server_wrapper:
            gsi_server_instance = gsi_server_wrapper[0]
            logger.info("[Main] GSI Uvicorn server instance captured.")
        else:
            logger.warning("[Main] Failed to capture GSI Uvicorn server instance. Check GSI server logs.")

        if auth_server_wrapper:
            auth_server_instance = auth_server_wrapper[0]
            logger.info("[Main] Auth Uvicorn server instance captured.")
        else:
            logger.warning("[Main] Failed to capture Auth Uvicorn server instance. Check Auth server logs.")

        logger.info("All services started. Handing over to system tray or wait loop...")

        run_system_tray(
            shutdown_event=shutdown_event,
            gsi_thread=gsi_thread,
            auth_thread=auth_thread,
            gsi_server_instance=gsi_server_instance,
            auth_server_instance=auth_server_instance,
            log_manager_instance=log_manager # Pass the singleton instance
        )

        logger.info("[Main] System tray/wait loop finished. Proceeding to final cleanup.")

    except KeyboardInterrupt:
        logger.info("[Main] KeyboardInterrupt caught in main try block. Ensuring shutdown...")
        if not shutdown_event.is_set(): # Check if already shutting down
             signal_handler_wrapper(signal.SIGINT, None) # Simulate SIGINT
    except Exception as e:
        logger.error(f"Unhandled exception in main function: {str(e)}")
        logger.error(traceback.format_exc())
        if not shutdown_event.is_set(): # Check if already shutting down
            signal_handler_wrapper(None, None) # Trigger shutdown
    finally:
        # Ensure shutdown is called if it hasn't been (e.g., if run_system_tray errors out)
        if not shutdown_event.is_set():
             logger.warning("[Main] Reached finally block without shutdown event being set. Forcing shutdown initiation.")
             signal_handler_wrapper(None, None) # Trigger shutdown

        logger.info("[Main] Application main function finished.")
        print("[Main] Application shutdown complete.")


if __name__ == "__main__":
    main()