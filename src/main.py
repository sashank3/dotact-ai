import os
import sys
import logging
import threading
import traceback
import asyncio
import signal
import concurrent.futures

# Add the project root to the Python path in development environment
# This must happen BEFORE any "src." imports
if not getattr(sys, 'frozen', False):
    # Get the absolute path to the project root (two directories up from main.py)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(project_root)
    print(f"Development mode: Added {project_root} to Python path")

# Now we can safely import from src
from src.exe.app_dirs import APP_DIRS, IS_FROZEN
from src.exe.logging_setup import configure_logging
from src.exe.config_manager import ensure_default_configs

def setup_logging():
    """Initialize the logging system using global configuration."""
    # Configure basic logging with proper directories
    from src.exe.logging_setup import configure_logging
    log_info = configure_logging()
    
    # Now import and configure advanced logging via log_manager
    # This will use the session directory created in configure_logging
    from src.logger.log_manager import log_manager
    from src.global_config import LOGGING_CONFIG
    
    # Log key information
    logging.info(f"[MAIN] Logging system initialized with session: {log_info['session_dir']}")
    logging.info(f"[MAIN] Application directories: {APP_DIRS}")
    logging.info("[MAIN] Full logging system initialized")

def setup_configs():
    """Set up configuration files."""
    # Ensure default configs are available
    ensure_default_configs()
    logging.info("[MAIN] Configuration setup complete")

# Import global AWS configuration so it's available to all modules that need it
def configure_aws():
    """Configure AWS SDK with credentials from config file.
    
    We're not returning a session but making sure the AWS SDK
    has the right credentials available globally.
    """
    from src.global_config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
    import boto3
    
    # Set defaults for boto3 that will apply to all clients and resources
    # This is thread-safe and will be used by any boto3 client created in any thread
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        boto3.setup_default_session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        logging.info("[MAIN] AWS SDK configured with explicit credentials")
    else:
        boto3.setup_default_session(region_name=AWS_REGION)
        logging.info("[MAIN] AWS SDK configured using default credential resolution")

def setup_api_configuration():
    """Configure API endpoints for cloud services."""
    from src.cloud.api import configure_process_query_api
    from src.global_config import PROCESS_QUERY_API_URL
    
    # Pass the pre-configured API URL from global config
    api_url = configure_process_query_api(process_query_url=PROCESS_QUERY_API_URL)
    return api_url

def setup_gsi_files():
    """Set up GSI configuration files if this is the first install."""
    from src.gsi.gsi_file_setup import gsi_file_setup
    from src.global_config import GLOBAL_CONFIG
    
    # Check if this is the first install
    first_install = GLOBAL_CONFIG.get("data", {}).get("gsi", {}).get("dota2", {}).get("first_install", False)
    
    if first_install:
        logging.info("[MAIN] First installation detected. Setting up GSI files...")
        gsi_file_setup()
    else:
        logging.info("[MAIN] Not first install, skipping GSI file setup")

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

def setup_event_loop_policy():
    """Configure the event loop policy for better async behavior."""
    if sys.platform == 'win32':
        # On Windows, use ProactorEventLoop which is more efficient
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Create a new event loop with larger buffer limits
    loop = asyncio.new_event_loop()
    
    # Set a reasonable default for number of tasks running simultaneously
    loop.set_default_executor(
        concurrent.futures.ThreadPoolExecutor(max_workers=min(32, os.cpu_count() + 4))
    )
    
    # Make this the default event loop for the application
    asyncio.set_event_loop(loop)
    
    logging.info("[MAIN] Configured event loop policy")
    return loop

def start_services():
    """
    Start all required services:
    1. GSI Server - Receives game state from Dota 2
    2. Auth Server - Handles user authentication
       (The Auth Server will start Chainlit when a user authenticates)
    """
    # Setup GSI files if needed before starting the GSI server
    setup_gsi_files()
    
    # Start GSI server
    gsi_thread = start_gsi_server()
    
    # Start auth server (which will start Chainlit when needed)
    auth_thread = start_auth_server()
    
    # Return threads for potential future management
    return {
        "gsi": gsi_thread,
        "auth": auth_thread
    }

def setup_signal_handlers(service_threads, loop):
    """Setup signal handlers for clean shutdown."""
    def shutdown_handler(sig, frame):
        logging.info(f"[MAIN] Received signal {sig}. Initiating graceful shutdown...")
        
        # Shutdown logging system
        from src.logger.log_manager import log_manager
        log_manager.shutdown()
        
        # Stop the event loop
        try:
            loop.stop()
        except:
            pass
        
        # Exit
        sys.exit(0)
    
    # Register SIGINT and SIGTERM handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

def main():
    """
    Main application entry point for Keenmind.
    
    This function orchestrates the startup sequence:
    1. Set up logging
    2. Set up configuration files
    3. Configure AWS SDK globally
    4. Configure API endpoints
    5. Start required services
    """
    try:
        # Setup logging first
        setup_logging()
        
        # Ensure configs are properly set up
        setup_configs()
        
        # Configure AWS SDK globally for any thread that needs it
        configure_aws()
        
        # Configure event loop policy
        loop = setup_event_loop_policy()
        
        # Configure API endpoints
        api_url = setup_api_configuration()
        logging.info(f"[MAIN] API URL configured: {api_url}")
        
        # Start services
        service_threads = start_services()
        
        # Setup signal handlers for clean shutdown
        setup_signal_handlers(service_threads, loop)
        
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
        # Clean up logging system
        try:
            from src.logger.log_manager import log_manager
            log_manager.shutdown()
        except:
            pass
        
        logging.info("[MAIN] Application shutdown complete.")

if __name__ == "__main__":
    main()
                                          