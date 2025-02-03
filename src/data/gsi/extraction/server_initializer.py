import logging
from src.data.gsi.extraction.game_state_handler import handle_game_state
from src.data.gsi.extraction.config_loader import load_config
from src.data.gsi.extraction.gsi_file_setup import gsi_file_setup
from dota2gsipy.server import GSIServer


def update(game_state):
    """
    Called when a new game state is received.
    :param game_state: The game state dictionary.
    """
    handle_game_state(game_state)


class CustomGSIServer(GSIServer):
    """
    Custom GSI server that processes incoming game state updates using the handle_game_state function.
    """

    def __init__(self, host_port, auth_token):
        super().__init__(host_port, auth_token)


def initialize_server():
    """
    Initializes the GSI server after setting up the required configuration.
    :return: Instance of CustomGSIServer.
    """
    # Step 1: Setup GSI file
    gsi_file_setup()

    # Step 2: Load configuration
    config = load_config()

    # Configure logging
    logging_level = config["logging"]["level"].upper()
    logging.basicConfig(level=getattr(logging, logging_level))
    logging.info("Initializing GSI server...")

    # Get server settings
    host = config["server"]["host"]
    port = config["server"]["port"]
    secret_token = config["auth"]["token"]

    # Initialize and return the server
    return CustomGSIServer((host, port), secret_token)
