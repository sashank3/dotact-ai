import logging
import threading

def setup_gsi_files():
    """Set up GSI configuration files."""
    from src.gsi.gsi_file_setup import gsi_file_setup
    
    logging.info("[GSI] Setting up GSI files...")
    gsi_file_setup()


def start_gsi_server(shutdown_event: threading.Event, server_instance_wrapper: list):
    """Start the GSI server in a separate thread."""
    from src.gsi.server import run_gsi_server
    from src.config import config

    # Get GSI host and port using properties
    host = config.gsi_host
    port = config.gsi_port

    logging.info(f"[GSI] Starting GSI server on {host}:{port}...")

    # Start GSI server in a separate thread, passing the event and wrapper
    gsi_thread = threading.Thread(
        target=run_gsi_server,
        kwargs={
            "host": host,
            "port": port,
            "shutdown_event": shutdown_event,
            "server_instance_wrapper": server_instance_wrapper
        },
        daemon=True # Keep daemon=True so thread doesn't block main exit if something goes wrong
    )
    gsi_thread.start()
    return gsi_thread