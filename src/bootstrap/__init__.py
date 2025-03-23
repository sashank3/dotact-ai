# Bootstrap module initialization
import sys
import os
import signal
import logging

def is_frozen():
    """Check if we're running as a PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False)

def get_application_root():
    """
    Get the root directory of the application
    
    In dev mode: Returns the repo root directory
    In prod mode: Returns the directory containing the executable
    """
    if is_frozen():
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # The executable itself is one level up from _MEIPASS
        return os.path.dirname(sys.executable)
    else:
        # In development mode, return the repo root
        # Assuming this file is in src/bootstrap/__init__.py
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/bootstrap
        src_dir = os.path.dirname(current_dir)  # src
        return os.path.dirname(src_dir)  # repo root

def setup_signal_handlers(service_threads, loop):
    """Setup signal handlers for clean shutdown."""
    def shutdown_handler(sig, frame):
        logging.info(f"[BOOTSTRAP] Received signal {sig}. Initiating graceful shutdown...")
        
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