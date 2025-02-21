import logging
import threading
import time
from src.global_config import GLOBAL_CONFIG

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

class GameStateManager:
    """Manages real-time game state data (Singleton)."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GameStateManager, cls).__new__(cls)
                cls._instance.latest_game_state = None
                cls._instance.logging_state = LoggingState()  # Add logging state
        return cls._instance

    def __init__(self):
        """No initialization needed as it's handled in __new__"""
        pass

    def update_state(self, new_state: dict):
        """Updates the latest game state."""
        with self._lock:
            if new_state and any(new_state.values()):
                if self.logging_state.should_log():
                    logging.info("[GAME STATE MANAGER] Updating game state: %s", new_state)
                self.latest_game_state = new_state

    def get_state(self):
        """Retrieves the latest stored game state."""
        with self._lock:
            if self.latest_game_state:
                return self.latest_game_state
            if self.logging_state.should_log():
                logging.warning("[GAME STATE MANAGER] No game state available")
            return None
