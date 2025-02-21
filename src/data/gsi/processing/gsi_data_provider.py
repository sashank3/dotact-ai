import logging
from src.data.gsi.extraction.state_manager import state_manager
from src.data.gsi.processing.game_state_processor import convert_game_state_to_text
from typing import Optional, Dict

def get_current_state() -> Optional[Dict]:
    """Get current game state"""
    state = state_manager.get_state()
    if state:
        logging.debug("[GSI PROVIDER] Retrieved state: %s", state)
    return state

def get_processed_state() -> str:
    """Get processed game state text"""
    state = get_current_state()
    if not state:
        logging.warning("[GSI PROVIDER] No state available")
        return "No game state available."
    
    processed = convert_game_state_to_text(state)
    logging.info("[GSI PROVIDER] Processed state: %s", processed)
    return processed
