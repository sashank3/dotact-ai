import subprocess
import logging
from src.logger.logger import setup_logging


def start_ui():
    setup_logging(log_file="ui_module.log")
    logging.info("[UI ORCHESTRATOR] Launching Chainlit UI...")

    # Hardcode the absolute path to chainlit_app.py on your machine
    chainlit_app_path = r"C:\Users\sasre\OneDrive\Documents\GitHub\dotact-ai\src\ui\chainlit_app.py"

    # Use the absolute path so there's no confusion about where chainlit_app.py lives
    subprocess.run(["chainlit", "run", chainlit_app_path])
