import logging
# import threading # Removed threading
from src.data.gsi.server.gsi_server import start_gsi_server  #This import is no longer needed
from src.logger.logger import setup_logging
from src.data.gsi.extraction.gsi_file_setup import gsi_file_setup
from src.data.gsi.processing.gsi_data_provider import get_processed_state

def gsi_orchestrator():
    """Sets up GSI config and starts the FastAPI server in a background thread."""
    setup_logging()
    logging.info("[GSI ORCHESTRATOR] Initializing...")

    # 1) Set up the GSI config file
    gsi_file_setup()

    logging.info("[GSI ORCHESTRATOR] GSI server launched in the background.")
