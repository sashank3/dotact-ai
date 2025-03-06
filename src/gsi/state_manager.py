"""File-based state manager for cross-process access"""
import logging
import json
import os
from typing import Optional, Dict, Set
from threading import Lock
from src.global_config import STATE_FILE_PATH, GSI_LOG_INTERVAL
import time
import datetime

# Configure logging
logger = logging.getLogger(__name__)

class HeroExtractor:
    """Extracts and tracks ally and enemy heroes from game state updates."""
    
    def __init__(self):
        """Initialize the hero extractor."""
    
    def extract_hero_lists(self, game_state: dict, state_manager_instance) -> None:
        """
        Extracts ally and enemy hero lists from the game state.
        Updates the ally_heroes and enemy_heroes in the state object.
        
        Args:
            game_state (dict): The current game state
            state_manager_instance: The StateManager instance to update
        """
        state = state_manager_instance.state
        
        # Initialize hero lists if they don't exist
        if "allies" not in state:
            state["allies"] = []
        if "enemies" not in state:
            state["enemies"] = []
            
        current_enemy_heroes_before_update = set(state["enemies"])
        
        minimap_data = game_state.get("minimap", {})
        if minimap_data:
            for obj_key, obj_data in minimap_data.items():
                hero_name = obj_data.get("name")
                if hero_name:
                    hero_name_cleaned = hero_name.replace("npc_dota_hero_", "")
                    image_type = obj_data.get("image", "")
                    
                    if "herocircle_self" in image_type or "herocircle" in image_type:  # Ally heroes
                        if hero_name_cleaned not in state["allies"]:
                            state["allies"].append(hero_name_cleaned)
                    elif image_type == "minimap_enemyicon":  # Enemy heroes
                        if hero_name_cleaned not in state["enemies"]:
                            state["enemies"].append(hero_name_cleaned)
        
        if len(state["allies"]) + len(state["enemies"]) == 10:
            state_manager_instance.heroes_tracked = True
            logger.info(
                f"All 10 heroes found for match {state_manager_instance.current_match_id}. "
                f"Tracking stopped. Allies: {state['allies']}, "
                f"Enemies: {state['enemies']}"
            )
        else:
            current_enemy_heroes_after_update = set(state["enemies"])
            if len(current_enemy_heroes_after_update) > len(current_enemy_heroes_before_update):  # New enemy hero detected
                logger.info(
                    f"New enemy hero detected for match {state_manager_instance.current_match_id}. "
                    f"Allies: {state['allies']}, "
                    f"Enemies: {state['enemies']}"
                )

class StateLogger:
    """Logs game state at regular intervals by saving complete state snapshots."""
    
    def __init__(self):
        """Initialize the state logger."""
        self.last_log_time = 0
        self.log_interval = GSI_LOG_INTERVAL  # Seconds between logs
        
        # Get session directory from environment
        self.session_dir = os.environ.get("SESSION_DIR")
        self.logging_enabled = self.session_dir is not None
        
        if not self.logging_enabled:
            logger.warning("SESSION_DIR not found in environment, state logging is disabled")
    
    def should_log(self):
        """Check if enough time has passed to log again."""
        if not self.logging_enabled:
            return False
            
        current_time = time.time()
        if current_time - self.last_log_time >= self.log_interval:
            self.last_log_time = current_time
            return True
        return False
    
    def log_state(self, state):
        """
        Save a complete snapshot of the current state to a timestamped file
        in the session directory when the log interval has passed.
        """
        if not self.should_log() or not state:
            return
            
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.session_dir, f"gsi_state_{timestamp}.json")
            
            with open(log_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"[STATE LOGGER] Saved state snapshot to {log_file}")
        except Exception as e:
            logger.error(f"[STATE LOGGER] Error saving state snapshot: {e}")

class StateManager:
    """Manages the game state, including loading, saving, and updating."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.state = {}
        self.state_file = STATE_FILE_PATH
        self.logger = StateLogger()
        self.hero_extractor = HeroExtractor()
        self._lock = Lock()
        
        # Track match and hero detection status, but not the heroes themselves
        self.current_match_id = None
        self.heroes_tracked = False
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        # Load initial state if available
        self.load_state()
    
    def update_state(self, new_state: Dict) -> None:
        """
        Update the current state with new data.
        
        Args:
            new_state (Dict): New state data to merge with existing state
        """
        with self._lock:
            try:
                # Check for match ID changes
                map_data = new_state.get("map", {})
                match_id = map_data.get("matchid")
                
                # Reset hero tracking if match ID changes
                if match_id != self.current_match_id:
                    # Reset heroes directly in state
                    self.state["allies"] = []
                    self.state["enemies"] = []
                    self.current_match_id = match_id
                    self.heroes_tracked = False
                    logger.info(f"Match ID changed, resetting hero lists. New Match ID: {match_id}")
                
                # Extract heroes if not fully tracked yet
                if not self.heroes_tracked:
                    self.hero_extractor.extract_hero_lists(new_state, self)
                
                # Merge the new state with the existing state
                for category, data in new_state.items():
                    if category not in self.state:
                        self.state[category] = {}
                    
                    # Update the category with new data
                    self.state[category].update(data)
                
                # Save the updated state
                self.save_state()
                
                # Log the state update
                self.logger.log_state(self.state)
                
            except Exception as e:
                logger.error(f"Error updating state: {str(e)}")
    
    def get_state(self) -> Optional[Dict]:
        """
        Get the current game state.
        
        Returns:
            Optional[Dict]: The current game state, or None if not available
        """
        with self._lock:
            return self.state if self.state else None
    
    def save_state(self) -> None:
        """Save the current state to the state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def load_state(self) -> None:
        """Load the state from the state file if it exists."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                
                # Check if we have pre-existing match data
                if "allies" in self.state and "enemies" in self.state:
                    # Set match ID from map data if available
                    if "map" in self.state and "matchid" in self.state["map"]:
                        self.current_match_id = self.state["map"]["matchid"]
                    
                    # Check if heroes are fully tracked
                    self.heroes_tracked = (
                        len(self.state.get("allies", [])) + 
                        len(self.state.get("enemies", [])) == 10
                    )
                
                logger.info(f"Loaded game state from {self.state_file}")
                if self.heroes_tracked:
                    logger.info(f"Restored hero tracking: Allies={self.state.get('allies', [])}, Enemies={self.state.get('enemies', [])}")
            else:
                logger.info(f"No state file found at {self.state_file}, starting with empty state")
                self.state = {}
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            self.state = {}

# Create a singleton instance
state_manager = StateManager() 