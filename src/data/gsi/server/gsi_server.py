import logging
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from src.data.gsi.extraction.game_state import GameStateManager

# Initialize FastAPI app
app = FastAPI()
game_state_manager = GameStateManager()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Disable Uvicorn access logs (prevents logging every request)
logging.getLogger("uvicorn.access").disabled = True


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
    """
    Receives and stores game state updates from Dota 2.
    """
    # Update manager with the raw JSON
    game_state_manager.update_state(update.dict())

    return {"status": "received"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def start_gsi_server():
    """
    Starts the FastAPI server (single-threaded) with modified logging settings.
    """
    logging.info("[GSI SERVER] Starting FastAPI server...")

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"  # Suppress request logs

    uvicorn.run(app, host="127.0.0.1", port=4000, log_config=log_config)
