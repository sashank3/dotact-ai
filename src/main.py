import logging
from dotenv import load_dotenv
from src.data.gsi.gsi import gsi_orchestrator
from src.ui.ui import start_ui


def main():
    # 1) Load environment variables
    load_dotenv()

    logging.info("[MAIN] Starting GSI pipeline...")
    # 2) Launch GSI in the background
    gsi_orchestrator()

    logging.info("[MAIN] Starting UI...")
    # 3) Run Chainlit UI in the foreground
    #    This call will block until the user stops Chainlit (Ctrl+C or otherwise).
    start_ui()

    logging.info("[MAIN] Exiting main...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
