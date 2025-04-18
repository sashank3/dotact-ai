"""
Game State Integration (GSI) server for Dota 2.
This module handles receiving and processing game state updates from Dota 2.
"""
import os
import sys
import logging
import json
import traceback
import threading
import aiofiles
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Simple, reliable path handling
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    # Running in development environment
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, root_dir)

# Import configuration
from src.config import config

# Import state manager
from src.gsi.state_manager import state_manager

# Configure logging
logger = logging.getLogger(__name__)

# Get the state file path from configuration
STATE_FILE_PATH = config.state_file_path
logger.info(f"Using game state file: {STATE_FILE_PATH}")

# Create FastAPI app
gsi_app = FastAPI(title="Keenplay GSI Server")

# Define the game state update model
class GameStateUpdate(BaseModel):
    provider: dict = {}
    map: dict = {}
    player: dict = {}
    hero: dict = {}
    abilities: dict = {}
    items: dict = {}
    buildings: dict = {}
    draft: dict = {}
    minimap: dict = {}

@gsi_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gsi-server"}

@gsi_app.post("/")
async def receive_game_state(update: GameStateUpdate):
    """Receive and process game state updates from Dota 2."""
    try:
        # Convert Pydantic model to dict
        update_dict = update.dict()
        
        # Log minimal info about the update
        hero_name = update_dict.get("hero", {}).get("name", "Unknown")
        game_time = update_dict.get("map", {}).get("game_time", 0)
        match_id = update_dict.get("map", {}).get("matchid", "Unknown")
        
        logger.debug(f"Received update: Hero={hero_name}, Game time={game_time}, Match ID={match_id}")
        
        # Update the state
        state_manager.update_state(update_dict)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        
        # Save the current state to the configured file asynchronously
        async with aiofiles.open(STATE_FILE_PATH, "w") as f:
            state_json = json.dumps(update_dict, indent=2)
            await f.write(state_json)
        
        logger.debug(f"Game state updated and saved to {STATE_FILE_PATH}")
        return {"status": "success", "message": "Game state updated"}
    except Exception as e:
        logger.error(f"Error processing game state update: {str(e)}")
        logger.error(f"Exception details: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

@gsi_app.on_event("startup")
async def startup_event():
    """Initialize resources on server startup."""
    logger.info("GSI server starting up")
    
    # Ensure the directory for the state file exists
    os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
    
    # Create an empty state file if it doesn't exist
    if not os.path.exists(STATE_FILE_PATH):
        async with aiofiles.open(STATE_FILE_PATH, "w") as f:
            await f.write(json.dumps({}))
        logger.info(f"Created empty game state file at {STATE_FILE_PATH}")

@gsi_app.on_event("shutdown")
async def shutdown_gsi_event():
    """Handle GSI server shutdown."""
    logger.info("[GSI Server] Shutting down")
    # Add any specific GSI cleanup tasks here if needed in the future

def run_gsi_server(
    host=None,
    port=None,
    shutdown_event: threading.Event = None,
    server_instance_wrapper: list = None
):
    """Run the GSI server and handle graceful shutdown."""
    # Use provided host/port or fall back to config
    host = host or config.gsi_host
    port = port or config.gsi_port

    # Log the configuration
    logger.info(f"Starting GSI server on {host}:{port}")

    # Configure Uvicorn server instance
    config_uvicorn = uvicorn.Config(
        app="src.gsi.server:gsi_app", # Reference the app instance directly
        host=host,
        port=port,
        reload=False, # Important: reload=False for programmatic control
        log_level="info",
        access_log=False, # Keep logs cleaner
        log_config=config.uvicorn_log_config # Use your custom log config
    )
    server = uvicorn.Server(config_uvicorn)

    # Store the server instance if a wrapper is provided
    if server_instance_wrapper is not None:
        server_instance_wrapper.append(server)

    # Start the server - this blocks until shutdown is triggered
    try:
        server.run()
        logger.info("[GSI Server] Uvicorn server stopped.")
    except Exception as e:
        logger.exception(f"CRITICAL ERROR during GSI server run() execution: {e}")
    finally:
        # Clean up the reference in the wrapper if it exists
        if server_instance_wrapper is not None and server in server_instance_wrapper:
            server_instance_wrapper.remove(server)
        logger.info("run_gsi_server function finished.")
