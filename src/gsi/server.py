"""
Game State Integration (GSI) server for Dota 2.
This module handles receiving and processing game state updates from Dota 2.
"""
import os
import sys
import logging
import json
import traceback
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import GSI_CONFIG, GSI_HOST, GSI_PORT, STATE_FILE_PATH

# Import state manager
from src.gsi.state_manager import state_manager

# Configure logging
logger = logging.getLogger(__name__)

# Get the state file path from configuration
STATE_FILE_PATH = GSI_CONFIG.get("state_file", "data/game_state.json")
logger.info(f"Using game state file: {STATE_FILE_PATH}")

# Create FastAPI app
gsi_app = FastAPI(title="Keenmind GSI Server")

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
        
        # Save the current state to the configured file
        with open(STATE_FILE_PATH, "w") as f:
            json.dump(update_dict, f)
        
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
        with open(STATE_FILE_PATH, "w") as f:
            json.dump({}, f)
        logger.info(f"Created empty game state file at {STATE_FILE_PATH}")

def run_gsi_server(host=None, port=None):
    """Run the GSI server."""
    # Use provided host/port or fall back to global config
    if host is None:
        host = GSI_HOST
    
    if port is None:
        port = GSI_PORT
    
    # Log the configuration
    logger.info(f"Starting GSI server on {host}:{port}")
    
    # Use uvicorn.Config and Server classes for thread-safe operation
    config = uvicorn.Config(
        app="src.gsi.server:gsi_app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=False  # Disable access logs completely
    )
    server = uvicorn.Server(config)
    server.run()
