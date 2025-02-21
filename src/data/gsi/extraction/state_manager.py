"""Simple state manager using events to handle game state updates"""
import logging
import time
from typing import Dict, Optional, Callable
from threading import Lock
from src.global_config import GLOBAL_CONFIG

class StateManager:
    def __init__(self):
        self._state: Optional[Dict] = None
        self._lock = Lock()
        self._subscribers: list[Callable] = []
        self._last_log_time = 0
        self._log_interval = GLOBAL_CONFIG["data"]["gsi"]["server"]["log_interval"]
        
    def should_log(self) -> bool:
        """Check if we should log based on interval"""
        current_time = time.time()
        if current_time - self._last_log_time >= self._log_interval:
            self._last_log_time = current_time
            return True
        return False

    def update_state(self, new_state: Dict) -> None:
        """Update state and notify subscribers"""
        with self._lock:
            if new_state and any(new_state.values()):
                self._state = new_state
                if self.should_log():
                    logging.info("[STATE MANAGER] State updated: %s", new_state)
                self._notify_subscribers()

    def get_state(self) -> Optional[Dict]:
        """Get current state"""
        with self._lock:
            if self.should_log():
                logging.info("[STATE MANAGER] Current state: %s", self._state)
            return self._state

    def subscribe(self, callback: Callable) -> None:
        """Add subscriber to state updates"""
        self._subscribers.append(callback)

    def _notify_subscribers(self) -> None:
        """Notify all subscribers of state update"""
        for callback in self._subscribers:
            try:
                callback(self._state)
            except Exception as e:
                logging.error(f"[STATE MANAGER] Error notifying subscriber: {e}")

# Global instance
state_manager = StateManager() 