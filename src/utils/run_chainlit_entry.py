# src/utils/run_chainlit_entry.py
import sys
import os
import runpy
import logging

def run_chainlit_main():
    """
    Main entry point for running Chainlit as a separate process.
    This function is called directly when the script is executed in "Chainlit mode".
    """
    # Use standard logging; configuration should be handled by log_manager
    # when chainlit loads the app and its imports.
    logger = logging.getLogger(__name__)

    logger.info("Chainlit helper script executing run_chainlit_main.")
    logger.debug(f"Helper script sys.argv: {sys.argv}")
    logger.debug(f"Helper script CWD: {os.getcwd()}")
    logger.debug(f"Helper script environment SESSION_DIR: {os.environ.get('SESSION_DIR')}")

    # --- Argument Parsing ---
    # Arguments expected:
    # sys.argv[0]: Path to this script or the main executable
    # sys.argv[1]: The helper script path (itself, when called from main.py)
    # sys.argv[2]: chainlit_app_path (e.g., 'src/ui/chainlit_app.py')
    # sys.argv[3]: port (e.g., '8001') - optional, defaults to 8001
    
    # Extract arguments, with appropriate index handling
    if len(sys.argv) < 3:
        # Log error using the logger
        error_msg = f"Helper script received insufficient arguments. Got: {sys.argv}"
        logger.error(error_msg)
        # Also print to stderr as a fallback in case logging isn't fully configured yet
        print(error_msg, file=sys.stderr)
        sys.exit("Usage: run_chainlit_entry.py <app_module_path> <port>")

    # When run via main.py special mode detection, the args will be at index 2, 3
    # When run directly as a script, they'll be at index 1, 2
    # Let's detect the correct indexes
    if 'run_chainlit_entry.py' in sys.argv[1]:
        # Called via main.py with run_chainlit_entry.py as arg1
        app_path_index = 2
        port_index = 3
    else:
        # Called directly as a script
        app_path_index = 1
        port_index = 2
    
    app_path_arg = sys.argv[app_path_index] if len(sys.argv) > app_path_index else "src/ui/chainlit_app.py"
    port_arg = sys.argv[port_index] if len(sys.argv) > port_index else "8001"

    logger.info(f"Preparing to run Chainlit with app: {app_path_arg} on port: {port_arg}")

    # --- Prepare sys.argv for Chainlit's internal argument parser ---
    # This mimics `chainlit run <app_path> --port <port> --headless`
    chainlit_argv = [
        "chainlit",       # Expected script name by chainlit's parser
        "run",
        app_path_arg,
        "--port", port_arg,
        "--headless"      # Essential for background running
    ]
    sys.argv = chainlit_argv
    logger.info(f"Modified sys.argv for runpy: {sys.argv}")

    # --- Execute Chainlit ---
    try:
        # Use runpy to execute the chainlit module's entry point.
        # This requires 'chainlit' package to be bundled correctly by PyInstaller.
        runpy.run_module("chainlit", run_name="__main__")
        logger.info("Chainlit run_module finished execution (likely normal shutdown).")
    except ModuleNotFoundError as e:
        logger.error(f"ModuleNotFoundError running chainlit: {e}. Is 'chainlit' package included in the build?", exc_info=True)
        logger.error(f"Current sys.path: {sys.path}")
        print(f"ModuleNotFoundError: {e}. Check PyInstaller bundling.", file=sys.stderr)
        sys.exit(f"Module not found: {e}")
    except ImportError as e:
        logger.error(f"ImportError running chainlit: {e}. Check imports within Chainlit or your app.", exc_info=True)
        print(f"ImportError: {e}.", file=sys.stderr)
        sys.exit(f"Import error: {e}")
    except SystemExit as e:
        # Log expected exits (like Chainlit shutdown)
        logger.info(f"Chainlit process initiated SystemExit with code: {e.code if hasattr(e, 'code') else e}")
        # Re-raise to ensure the subprocess exits correctly
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error running chainlit via runpy: {e}", exc_info=True)
        print(f"Failed to run chainlit: {e}", file=sys.stderr)
        sys.exit(f"Failed to run chainlit: {e}")

# --- Script Entry Point ---
if __name__ == "__main__":
    try:
        run_chainlit_main()
    except SystemExit as e:
        # Allow SystemExit to propagate naturally for correct exit codes
        sys.exit(e.code if hasattr(e, 'code') else e)
    except Exception as e:
        # Catch any other unexpected errors during script execution
        # Use logging if possible, otherwise print
        try:
            logging.getLogger(__name__).error(f"Critical error in helper script __main__: {e}", exc_info=True)
        except Exception: # Catch potential logging errors too
            print(f"Critical error in helper script __main__: {e}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero code on failure