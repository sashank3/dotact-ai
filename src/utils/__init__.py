# src/utils/__init__.py
import os
import sys
import asyncio
import concurrent.futures
import logging
import threading
import time
import signal
import webbrowser
from PIL import Image
import pystray

# Re-export paths functions for easy access
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

# Import necessary components from other modules
from src.bootstrap import is_frozen

# Get a logger instance for utility functions
logger = logging.getLogger(__name__)

# --- Original Utils ---

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
    gsi_server_instance,
    auth_server_instance,
    log_manager_instance, # Accept log_manager instance
    signum=None
):
    """Gracefully shuts down all application components."""
    shutdown_logger = logging.getLogger(__name__) # Use logger from this module

    if shutdown_event.is_set():
        return

    if signum:
         signal_name = getattr(signal, f'SIG{signal.Signals(signum).name}', f'Signal {signum}')
         shutdown_logger.info(f"Received signal {signal_name}. Initiating graceful shutdown...")
    else:
         shutdown_logger.info("Initiating graceful shutdown...")

    shutdown_event.set()

    auth_stopped = False
    gsi_stopped = False

    # Use the passed-in server instances
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

    # Use the passed-in threads
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
            print(f"Error shutting down log listener: {log_shutdown_err}", file=sys.stderr)
    elif hasattr(log_manager_instance, 'shutdown'):
         try:
             log_manager_instance.shutdown()
         except Exception as log_shutdown_err:
             print(f"Error calling log_manager.shutdown(): {log_shutdown_err}", file=sys.stderr)
    else:
        print("Could not find suitable shutdown method on log_manager.", file=sys.stderr)

    print("Graceful shutdown process finished.")

# --- System Tray Logic ---

def _open_keenplay(icon, item):
    """Callback function to open the application in the browser."""
    from src.config import config
    
    # Use AUTH_PORT as the entry point which handles login/redirects
    url = f"http://localhost:{config.auth_port}/direct-login"
    logger.info(f"Tray action: Opening KeenPlay at {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")

def _exit_action(icon, item, shutdown_event, gsi_thread, auth_thread, gsi_server_instance, auth_server_instance, log_manager_instance):
    """Callback function to initiate shutdown and stop the tray icon."""
    logger.info("Tray action: Exit selected. Initiating shutdown.")
    initiate_shutdown(
        shutdown_event=shutdown_event,
        gsi_thread=gsi_thread,
        auth_thread=auth_thread,
        gsi_server_instance=gsi_server_instance,
        auth_server_instance=auth_server_instance,
        log_manager_instance=log_manager_instance, # Pass the instance
        signum=None # Indicate manual shutdown via tray
    )
    logger.debug("Stopping tray icon loop.")
    if icon:
        icon.stop() # Stop the pystray event loop

def run_system_tray(shutdown_event, gsi_thread, auth_thread, gsi_server_instance, auth_server_instance, log_manager_instance):
    """Sets up and runs the system tray icon or waits if not applicable."""
    tray_icon = None

    if is_frozen(): # Only attempt to run tray icon in frozen mode
        icon_path = config.chainlit_tray_icon_path
        logger.info(f"Attempting to load icon from: {icon_path}")

        if icon_path and os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
                logger.info("Icon image loaded successfully.")

                # Use lambda to pass necessary arguments to _exit_action
                exit_callback = lambda icon, item: _exit_action(
                    icon, item, shutdown_event, gsi_thread, auth_thread,
                    gsi_server_instance, auth_server_instance, log_manager_instance
                )

                menu = (
                    pystray.MenuItem('Open KeenPlay', _open_keenplay, default=True),
                    pystray.MenuItem('Exit', exit_callback)
                )

                tray_icon = pystray.Icon("KeenPlay", image, "KeenPlay", menu)
                logger.info("System tray icon configured.")

            except FileNotFoundError:
                logger.error(f"Icon file not found at {icon_path}")
            except Exception as e:
                logger.error(f"Failed to create system tray icon: {e}", exc_info=True)
        else:
            logger.error(f"Icon file path is invalid or does not exist: {icon_path}")

    # --- Main Loop Logic ---
    if tray_icon: # This implies is_frozen() was true and icon creation succeeded
        logger.info("Starting system tray icon loop (frozen mode)...")
        try:
            # This runs the tray icon and blocks the main thread
            tray_icon.run()
            logger.info("System tray icon loop finished.")
        except Exception as e:
             logger.error(f"Error running tray icon: {e}", exc_info=True)
        finally:
            # Ensure shutdown is triggered even if tray loop exits unexpectedly
            if not shutdown_event.is_set():
                 logger.warning("Tray icon loop exited unexpectedly. Forcing shutdown.")
                 # Manually trigger shutdown (similar to signal handler)
                 initiate_shutdown(
                     shutdown_event, gsi_thread, auth_thread,
                     gsi_server_instance, auth_server_instance, log_manager_instance, signum=None
                 )
    else: # Keep original wait loop for non-frozen (dev) mode or if tray failed
         if not tray_icon and is_frozen():
              logger.warning("Running in frozen mode BUT tray icon failed to load. Falling back to simple wait loop.")
         elif not is_frozen():
              logger.info("Running in development mode. Using simple wait loop.")

         logger.info("Application running. Press Ctrl+C to exit.")
         try:
             while not shutdown_event.is_set():
                 # Keep the main thread alive, allowing background threads to run
                 # Optional: Check thread health periodically
                 if gsi_thread and not gsi_thread.is_alive():
                     logger.warning("GSI thread unexpectedly terminated. Initiating shutdown.")
                     # Call initiate_shutdown directly via wrapper function
                     initiate_shutdown(
                         shutdown_event, gsi_thread, auth_thread,
                         gsi_server_instance, auth_server_instance, log_manager_instance, signum=None
                     )
                     break # Exit the loop after initiating shutdown
                 if auth_thread and not auth_thread.is_alive():
                     logger.warning("Auth thread unexpectedly terminated. Initiating shutdown.")
                     initiate_shutdown(
                         shutdown_event, gsi_thread, auth_thread,
                         gsi_server_instance, auth_server_instance, log_manager_instance, signum=None
                     )
                     break # Exit the loop after initiating shutdown

                 time.sleep(1) # Check every second
         except KeyboardInterrupt:
              logger.info("KeyboardInterrupt received (Ctrl+C).")
              # Signal handler should take over, but call initiate_shutdown defensively if needed
              if not shutdown_event.is_set():
                 initiate_shutdown(
                     shutdown_event, gsi_thread, auth_thread,
                     gsi_server_instance, auth_server_instance, log_manager_instance, signum=signal.SIGINT
                 )
         finally:
             logger.info("Main wait loop finished.")