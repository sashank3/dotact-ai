"""File-based state manager for cross-process access"""
import logging
import json
import os
from typing import Optional, Dict
from threading import Lock
from src.global_config import GLOBAL_CONFIG, BASE_DIR
import time
import datetime
from src.logger.log_manager import log_manager
from src.data.gsi.extraction.hero_extractor import extract_hero_lists

class StateLogger:
    def __init__(self):
        self.last_log = 0
        self.interval = GLOBAL_CONFIG["data"]["gsi"]["server"]["log_interval"]
        self.log_dir = os.environ["SESSION_DIR"]
        
    def should_log(self):
        current_time = time.time()
        if current_time - self.last_log >= self.interval:
            self.last_log = current_time
            return True
        return False

    def log_state(self, state):
        if not state:
            return
            
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = os.environ["SESSION_DIR"]
            log_file = os.path.join(session_dir, f"gsi_state_{timestamp}.json")
            
            with open(log_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            logging.info(f"[STATE LOGGER] Saved state snapshot to {log_file}")
        except Exception as e:
            logging.error(f"[STATE LOGGER] Error saving state: {e}")

class StateManager:
    def __init__(self):
        self._lock = Lock()
        self._state_file = os.path.join(BASE_DIR, GLOBAL_CONFIG["data"]["gsi"]["state_file"])
        self.logger = StateLogger()
        self.ally_heroes = set()
        self.enemy_heroes = set()
        self.current_match_id = None
        self.heroes_tracked = False
        
    def update_state(self, new_state: Dict) -> None:
        """Save state directly to file and track heroes."""
        with self._lock:
            if not new_state or not any(new_state.values()):
                return

            map_data = new_state.get("map", {})
            match_id = map_data.get("matchid")

            # Reset hero tracking if match ID changes
            if match_id != self.current_match_id:
                self.ally_heroes = set()
                self.enemy_heroes = set()
                self.current_match_id = match_id
                self.heroes_tracked = False
                logging.info(f"[STATE MANAGER] Match ID changed, resetting hero lists. New Match ID: {match_id}")

            if not self.heroes_tracked:
                extract_hero_lists(new_state, self)

            # Add ally_heroes and enemy_heroes to the state before saving
            new_state["allies"] = list(self.ally_heroes)
            new_state["enemies"] = list(self.enemy_heroes)

            try:
                logging.debug(f"Saving to: {self._state_file}")
                os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
                with open(self._state_file, 'w') as f:
                    json.dump(new_state, f)
                logging.debug("State saved successfully")
                
                if self.logger.should_log():
                    self.logger.log_state(new_state)
            except Exception as e:
                logging.error(f"[STATE MANAGER] Error saving state: {e}")

    def get_state(self) -> Optional[Dict]:
        """Read state directly from file"""
        with self._lock:
            try:
                if os.path.exists(self._state_file):
                    with open(self._state_file, 'r') as f:
                        return json.load(f)
                return None
            except Exception as e:
                logging.error(f"[STATE MANAGER] Error loading state: {e}")
                return None

# Global instance
state_manager = StateManager() 