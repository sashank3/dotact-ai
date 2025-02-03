import logging
from src.data.gsi.utils.logger import setup_logging
from src.data.gsi.extraction.extraction import extraction
# Import other orchestrators as needed


def gsi_orchestrator():
    """
    Main orchestrator for the GSI module. Calls individual orchestrators for extraction,
    cleaning, processing, etc.
    """
    setup_logging()  # Initialize logging

    try:
        logging.info("Running GSI extraction orchestrator...")
        extraction()

        # Call other orchestrators as needed
        # logging.info("Running GSI cleaning orchestrator...")
        # cleaning_orchestrator()

        # logging.info("Running GSI processing orchestrator...")
        # processing_orchestrator()

        logging.info("GSI module orchestrator completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred in the GSI module orchestrator: {e}")


if __name__ == "__main__":
    gsi_orchestrator()
