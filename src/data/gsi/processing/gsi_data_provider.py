from src.data.gsi.extraction.game_state import GameStateManager
from src.data.gsi.processing.game_state_processor import convert_game_state_to_text


def fetch_and_process_game_state() -> str:
    """
    Retrieves the latest raw data from the GameStateManager,
    converts it to text, and returns it.
    """
    latest_raw_state = GameStateManager().get_state()
    return convert_game_state_to_text(latest_raw_state)
