import os
import sys
import logging
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger.log_manager import log_manager
from src.data.gsi.gsi import gsi_orchestrator
from src.ui.ui import start_ui


def main():
    # 1) Load environment variables
    load_dotenv()

    # 2) Start GSI pipeline
    logging.info("[MAIN] Starting GSI pipeline...")
    gsi_orchestrator()

    logging.info("[MAIN] Starting UI...")
    # 3) Run Chainlit UI in the foreground
    start_ui()

    logging.info("[MAIN] Exiting main...")


if __name__ == "__main__":
    main()
