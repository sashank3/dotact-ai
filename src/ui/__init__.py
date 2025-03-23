import logging
import threading

def start_auth_server():
    """
    Start the authentication server.
    
    Note: The auth server is responsible for starting Chainlit when a user
    successfully authenticates. We don't need to start Chainlit separately.
    """
    from src.ui.auth import run_auth_server
    from src.config import config
    
    logging.info(f"[UI] Starting authentication server on port {config.auth_port} and Chainlit on port {config.chainlit_port}...")
    
    # Start auth server in a separate thread
    auth_thread = threading.Thread(
        target=run_auth_server,
        kwargs={"host": "0.0.0.0", "port": config.auth_port},
        daemon=True
    )
    auth_thread.start()
    return auth_thread
