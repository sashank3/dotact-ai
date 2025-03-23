import logging
import threading

def setup_gsi_files():
    """Set up GSI configuration files if this is the first install."""
    from src.gsi.gsi_file_setup import gsi_file_setup
    from src.config import config
    
    # Check if this is the first install using the config manager
    first_install = config.get("data", "gsi", "dota2", "first_install", default=False)
    
    if first_install:
        logging.info("[GSI] First installation detected. Setting up GSI files...")
        gsi_file_setup()
    else:
        logging.info("[GSI] Not first install, skipping GSI file setup")

def start_gsi_server():
    """Start the GSI server in a separate thread."""
    from src.gsi.server import run_gsi_server
    from src.config import config
    
    # Get GSI host and port using properties
    host = config.gsi_host
    port = config.gsi_port
    
    logging.info(f"[GSI] Starting GSI server on {host}:{port}...")
    
    # Start GSI server in a separate thread
    gsi_thread = threading.Thread(
        target=run_gsi_server,
        kwargs={"host": host, "port": port},
        daemon=True
    )
    gsi_thread.start()
    return gsi_thread 