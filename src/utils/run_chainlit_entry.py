# src/utils/run_chainlit_entry.py
import sys
import os
import runpy
import logging

def run_chainlit_main():
    # Get logger instance
    logger = logging.getLogger(__name__)
    logger.info("Chainlit helper script executing run_chainlit_main.")
    logger.debug(f"Helper script sys.argv: {sys.argv}")
    logger.debug(f"Helper script CWD: {os.getcwd()}")
    logger.debug(f"Helper script environment SESSION_DIR: {os.environ.get('SESSION_DIR')}")
    
    # Check arguments
    if len(sys.argv) < 3:
        logger.error(f"Helper script received insufficient arguments: {sys.argv}")
        sys.exit("Usage: run_chainlit_entry.py <app_module_path> <port>")

    app_path_arg = sys.argv[1]
    port_arg = sys.argv[2]
    
    # Set up sys.argv for Chainlit's internal argument parser
    chainlit_argv = [
        "chainlit",  # Expected by chainlit's parser
        "run",
        app_path_arg,
        "--port", port_arg,
        "--headless"
    ]
    sys.argv = chainlit_argv
    
    try:
        # Use runpy to execute the chainlit module
        runpy.run_module("chainlit", run_name="__main__")
    except Exception as e:
        logger.error(f"Error running chainlit via runpy: {e}", exc_info=True)
        sys.exit(f"Failed to run chainlit: {e}")

if __name__ == "__main__":
    try:
         run_chainlit_main()
    except SystemExit as e:
         sys.exit(e.code)
    except Exception as e:
         try:
            logging.getLogger(__name__).error(f"Critical error in helper script __main__: {e}", exc_info=True)
         except Exception: # Catch potential logging errors too
            print(f"Critical error in helper script __main__: {e}", file=sys.stderr)
         sys.exit(1) # Exit with a non-zero code on failure