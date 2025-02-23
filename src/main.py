import os
import sys
import logging
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # Initialize FIRST and only once
    from src.logger.log_manager import log_manager  # ← Triggers initialization
    
    # Start components AFTER setting SESSION_DIR
    from src.data.gsi.gsi import gsi_orchestrator
    from src.ui.ui import start_ui
    
    load_dotenv()
    
    # Initialize logging FIRST
    logging.info("[MAIN] Starting GSI pipeline...")
    gsi_orchestrator()
    
    logging.info("[MAIN] Starting UI...")
    start_ui()


if __name__ == "__main__":
    main()
