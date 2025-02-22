import logging
from src.data.gsi.extraction.state_manager import state_manager
from src.data.gsi.processing.game_state_processor import convert_game_state_to_text
from typing import Optional, Dict

def get_current_state():
    """Get current game state from file"""
    return state_manager.get_state()

def get_processed_state() -> str:
    """Get processed game state text"""
    state = get_current_state()
    if not state:
        return "No game state available."
    return convert_game_state_to_text(state)
