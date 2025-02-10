import logging
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from src.data.gsi.extraction.game_state import GameStateManager
from src.data.gsi.processing.game_state_processor import convert_game_state_to_text

# Initialize FastAPI app
app = FastAPI()
game_state_manager = GameStateManager()


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
    # 1) Update manager with the raw JSON
    game_state_manager.update_state(update.dict())
    logging.info("[GSI SERVER] Game state updated.")

    # 2) (Optional) Convert to text right here just to log it each time
    processed_text = convert_game_state_to_text(update.dict())
    logging.info(f"[GSI SERVER] Processed snippet:\n{processed_text}")

    return {"status": "received"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def start_gsi_server():
    """
    Starts the FastAPI server (single-threaded).
    """
    logging.info("[GSI SERVER] Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=4000, log_level="info")
