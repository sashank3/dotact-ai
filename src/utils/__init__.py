import os
import sys
import asyncio
import concurrent.futures
import logging

# Re-export paths functions for easy access throughout the app
from src.utils.paths import get_config_path, get_user_data_path, get_logs_path

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
    
    logging.info("[UTILS] Configured event loop policy")
    return loop 