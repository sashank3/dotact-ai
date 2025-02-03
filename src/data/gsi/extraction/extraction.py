import logging
from src.data.gsi.extraction.server_initializer import initialize_server


def extraction():
    """
    Main orchestrator for the GSI server. Starts the server.
    """
    # Initialize the custom GSI server
    server = initialize_server()

    # Start the server
    try:
        server.start_server()
    except KeyboardInterrupt:
        logging.info("GSI server stopped.")


if __name__ == "__main__":
    extraction()
