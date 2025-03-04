import os
import sys
import logging
import threading
import traceback
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_environment():
    """Set up the environment by loading environment variables."""
    load_dotenv()
    
    # Basic logging setup with debug level
    logging.basicConfig(
        level=logging.DEBUG,  # Changed from INFO to DEBUG
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logging.info("[MAIN] Environment variables loaded from .env file")

def setup_logging():
    """Initialize the logging system using global configuration."""
    from src.logger.log_manager import log_manager  # ← Triggers initialization
    from src.global_config import LOGGING_CONFIG
    
    # Apply logging configuration from global config
    logging.info(f"[MAIN] Setting up logging with config: {LOGGING_CONFIG}")
    logging.info("[MAIN] Logging system initialized")

def setup_api_configuration():
    """Configure API endpoints for cloud services."""
    from src.cloud.api import configure_process_query_api
    api_url = configure_process_query_api()
    return api_url

def start_gsi_server():
    """Start the GSI server in a separate thread."""
    from src.gsi.server import run_gsi_server
    from src.global_config import GSI_HOST, GSI_PORT
    
    logging.info(f"[MAIN] Starting GSI server on {GSI_HOST}:{GSI_PORT}...")
    
    # Start GSI server in a separate thread
    gsi_thread = threading.Thread(
        target=run_gsi_server,
        kwargs={"host": GSI_HOST, "port": GSI_PORT},
        daemon=True
    )
    gsi_thread.start()
    return gsi_thread

def start_auth_server():
    """
    Start the authentication server.
    
    Note: The auth server is responsible for starting Chainlit when a user
    successfully authenticates. We don't need to start Chainlit separately.
    """
    from src.ui.auth import run_auth_server
    from src.global_config import AUTH_PORT, CHAINLIT_PORT
    
    logging.info(f"[MAIN] Starting authentication server on port {AUTH_PORT} and Chainlit on port {CHAINLIT_PORT}...")
    
    # Start auth server in a separate thread
    auth_thread = threading.Thread(
        target=run_auth_server,
        kwargs={"host": "0.0.0.0", "port": AUTH_PORT},
        daemon=True
    )
    auth_thread.start()
    return auth_thread

def start_services():
    """
    Start all required services:
    1. GSI Server - Receives game state from Dota 2
    2. Auth Server - Handles user authentication
       (The Auth Server will start Chainlit when a user authenticates)
    """
    # Start GSI server
    gsi_thread = start_gsi_server()
    
    # Start auth server (which will start Chainlit when needed)
    auth_thread = start_auth_server()
    
    # Return threads for potential future management
    return {
        "gsi": gsi_thread,
        "auth": auth_thread
    }

def main():
    """
    Main application entry point for Keenmind.
    
    This function orchestrates the startup sequence:
    1. Load environment variables
    2. Set up logging
    3. Configure API endpoints
    4. Start required services
    """
    try:
        # Setup environment
        setup_environment()
        
        # Setup logging
        setup_logging()
        
        # Configure API endpoints
        api_url = setup_api_configuration()
        logging.info(f"[MAIN] API URL configured: {api_url}")
        
        # Start services
        service_threads = start_services()
        
        # Keep the main thread alive
        logging.info("[MAIN] All services started. Press Ctrl+C to exit.")
        
        # Join threads to keep the main thread alive
        for name, thread in service_threads.items():
            if thread and thread.is_alive():
                thread.join()
                
    except KeyboardInterrupt:
        logging.info("[MAIN] Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logging.error(f"[MAIN] Error in main function: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        logging.info("[MAIN] Application shutdown complete.")

if __name__ == "__main__":
    main()
                                          