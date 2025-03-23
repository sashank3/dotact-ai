import traceback

# Import bootstrap to initialize environment
from src.bootstrap import is_frozen, get_application_root

# Import the log_manager first to ensure proper logging configuration
from src.logger.log_manager import log_manager
import logging

# Get a logger instance for this module
logger = logging.getLogger(__name__)

logger.info(f"Starting application in {'production' if is_frozen() else 'development'} mode")
logger.info(f"Application root: {get_application_root()}")

# Import utils early to initialize path resolution
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

logger.info(f"Config path: {get_config_path()}")
logger.info(f"User data path: {get_user_data_path()}")
logger.info(f"Logs path: {get_logs_path()}")

def main():
    """
    Main application entry point.
    
    This function directly coordinates all application initialization and startup.
    """
    try:
        # Configure event loop policy
        from src.utils import setup_event_loop_policy
        loop = setup_event_loop_policy()
        
        # Configure API endpoints
        from src.cloud import setup_api_configuration
        api_url = setup_api_configuration()
        logger.info(f"API URL configured: {api_url}")
        
        # Setup GSI files if needed
        from src.gsi import setup_gsi_files
        setup_gsi_files()
        
        # Start services
        from src.gsi import start_gsi_server
        from src.ui import start_auth_server
        
        # Start GSI server
        gsi_thread = start_gsi_server()
        
        # Start auth server
        auth_thread = start_auth_server()
        
        service_threads = {
            "gsi": gsi_thread,
            "auth": auth_thread
        }
        
        # Setup signal handlers for clean shutdown
        from src.bootstrap import setup_signal_handlers
        setup_signal_handlers(service_threads, loop)
        
        # Keep the main thread alive
        logger.info("All services started. Press Ctrl+C to exit.")
        
        # Join threads to keep the main thread alive
        for name, thread in service_threads.items():
            if thread and thread.is_alive():
                thread.join()
                
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up logging system
        try:
            log_manager.shutdown()
        except Exception as e:
            print(f"Error shutting down log manager: {str(e)}")
        
        logger.info("Application shutdown complete.")

if __name__ == "__main__":
    main() 