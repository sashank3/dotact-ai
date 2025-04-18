import logging
import threading

def start_auth_server(shutdown_event: threading.Event, server_instance_wrapper: list):
    """
    Start the authentication server.

    Note: The auth server is responsible for starting Chainlit when a user
    successfully authenticates. We don't need to start Chainlit separately.
    """
    from src.ui.auth import run_auth_server
    from src.config import config

    logging.info(f"[UI] Starting authentication server on port {config.auth_port} and Chainlit on port {config.chainlit_port}...")

    # ****** MODIFIED thread arguments ******
    # Start auth server in a separate thread
    auth_thread = threading.Thread(
        target=run_auth_server,
        kwargs={
            "host": "0.0.0.0", # Keep host specific if needed
            "port": config.auth_port,
            "shutdown_event": shutdown_event,
            "server_instance_wrapper": server_instance_wrapper
        },
        daemon=True # Keep daemon=True
    )
    # ****** END MODIFICATION ******
    auth_thread.start()
    return auth_thread
