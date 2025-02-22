import logging
import uvicorn
import time
from fastapi import FastAPI
from pydantic import BaseModel
from src.global_config import GLOBAL_CONFIG
from src.data.gsi.extraction.state_manager import state_manager

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Disable Uvicorn access logs (prevents logging every request)
logging.getLogger("uvicorn.access").disabled = True

class LoggingState:
    """Class to maintain logging state"""
    def __init__(self):
        self.last_log_time = 0
        self.interval = GLOBAL_CONFIG["data"]["gsi"]["server"]["log_interval"]

    def should_log(self):
        current_time = time.time()
        if current_time - self.last_log_time >= self.interval:
            self.last_log_time = current_time
            return True
        return False

# Create a single logging state instance
logging_state = LoggingState()

class GameStateUpdate(BaseModel):
    """Schema for receiving game state updates."""
    map: dict = {}
    player: dict = {}
    hero: dict = {}
    abilities: dict = {}
    items: dict = {}
    buildings: dict = {}
    draft: dict = {}

@app.post("/")
async def receive_game_state(update: GameStateUpdate):
    """Receives and stores game state updates from Dota 2."""
    state_dict = update.dict()
    if not any(state_dict.values()):
        logging.debug("[GSI SERVER] Received empty update")
        return {"status": "empty"}
    
    logging.debug("[GSI SERVER] Received state update")
    state_manager.update_state(state_dict)
    return {"status": "received"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

def start_gsi_server():
    """
    Starts the FastAPI server (single-threaded) with modified logging settings.
    """
    logging.info(f"Starting server on port 4000")
    logging.info(f"GSI config path: {GLOBAL_CONFIG['data']['gsi']['dota2']['gsi_config_path']}")
    
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"  # Suppress request logs

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=4000,
        log_config=log_config,
        workers=1
    )
