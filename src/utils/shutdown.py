# src/utils/shutdown.py (Minimal Change Version)

import logging
import threading
import time
import subprocess
import sys
import os

logger = logging.getLogger(__name__)

def terminate_application(
    shutdown_event: threading.Event,
    chainlit_process_handle,
    gsi_thread: threading.Thread,
    auth_thread: threading.Thread
):
    """
    Performs shutdown of application components (minimal change version).
    Terminates Chainlit process and relies on daemon threads for server exit.

    Args:
        shutdown_event: The threading.Event signaling shutdown.
        chainlit_process_handle: The subprocess.Popen handle for Chainlit.
        gsi_thread: The thread running the GSI server.
        auth_thread: The thread running the Auth server.
    """
    logger.info("Executing terminate_application (minimal change version)...")

    if not shutdown_event.is_set():
        logger.warning("terminate_application called but shutdown_event was not set. Setting it now.")
        shutdown_event.set()

    # 1. Stop Uvicorn Servers - REMOVED (cannot do gracefully without instances)
    # logger.info("Skipping graceful Uvicorn shutdown (no server instances).")

    # 2. Terminate Chainlit Process (if handle exists)
    # Add a small delay maybe?
    time.sleep(0.5)
    if chainlit_process_handle and chainlit_process_handle.poll() is None:
        logger.info(f"Terminating Chainlit subprocess (PID: {chainlit_process_handle.pid})...")
        chainlit_process_handle.terminate() # Send SIGTERM
        try:
            chainlit_process_handle.wait(timeout=5) # Wait up to 5 seconds
            logger.info("Chainlit subprocess terminated.")
        except subprocess.TimeoutExpired:
            logger.warning("Chainlit subprocess did not terminate gracefully, killing.")
            chainlit_process_handle.kill() # Send SIGKILL
            try:
                 chainlit_process_handle.wait(timeout=2)
                 logger.info("Chainlit subprocess killed.")
            except Exception as e:
                 logger.error(f"Error waiting for Chainlit process kill: {e}")
        except Exception as e:
            logger.error(f"Error terminating/waiting for Chainlit process: {e}")
    elif chainlit_process_handle:
         logger.info(f"Chainlit subprocess (PID: {chainlit_process_handle.pid}) already terminated.")
    else:
         logger.info("No active Chainlit subprocess handle found to terminate.")


    # 3. Attempt to Join Server Threads (with short timeout)
    # These threads likely won't exit cleanly as server.run() blocks,
    # but we attempt to join before main process exits.
    if gsi_thread and gsi_thread.is_alive():
        logger.info("Attempting to join GSI server thread (will likely time out)...")
        gsi_thread.join(timeout=1) # Short timeout
        if gsi_thread.is_alive():
            logger.warning("GSI server thread did not join (as expected).")
    if auth_thread and auth_thread.is_alive():
        logger.info("Attempting to join Auth server thread (will likely time out)...")
        auth_thread.join(timeout=1) # Short timeout
        if auth_thread.is_alive():
             logger.warning("Auth server thread did not join (as expected).")

    logger.info("Graceful shutdown sequence complete (servers exit via daemon thread termination).")

    # Logging shutdown handled by atexit

    sys.exit(0) # Exit the main process. Daemon threads will be killed now.