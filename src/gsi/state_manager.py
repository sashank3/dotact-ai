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
        self.previous_enemy_heroes = set()
    
    def extract_hero_lists(self, game_state: dict, state_manager_instance) -> None:
        """
        Extracts ally and enemy hero lists from the game state.
        Updates the ally_heroes and enemy_heroes sets in the provided StateManager instance.
        
        Args:
            game_state (dict): The current game state
            state_manager_instance: The StateManager instance to update
        """
        current_enemy_heroes_before_update = set(state_manager_instance.enemy_heroes)
        
        minimap_data = game_state.get("minimap", {})
        if minimap_data:
            for obj_key, obj_data in minimap_data.items():
                hero_name = obj_data.get("name")
                if hero_name:
                    hero_name_cleaned = hero_name.replace("npc_dota_hero_", "")
                    image_type = obj_data.get("image", "")
                    
                    if "herocircle_self" in image_type or "herocircle" in image_type:  # Ally heroes
                        state_manager_instance.ally_heroes.add(hero_name_cleaned)
                    elif image_type == "minimap_enemyicon":  # Enemy heroes
                        state_manager_instance.enemy_heroes.add(hero_name_cleaned)
        
        if len(state_manager_instance.ally_heroes) + len(state_manager_instance.enemy_heroes) == 10:
            state_manager_instance.heroes_tracked = True
            logger.info(
                f"All 10 heroes found for match {state_manager_instance.current_match_id}. "
                f"Tracking stopped. Allies: {state_manager_instance.ally_heroes}, "
                f"Enemies: {state_manager_instance.enemy_heroes}"
            )
        else:
            current_enemy_heroes_after_update = set(state_manager_instance.enemy_heroes)
            if len(current_enemy_heroes_after_update) > len(current_enemy_heroes_before_update):  # New enemy hero detected
                logger.debug(
                    f"New enemy hero detected for match {state_manager_instance.current_match_id}. "
                    f"Allies: {state_manager_instance.ally_heroes}, "
                    f"Enemies: {state_manager_instance.enemy_heroes}"
                )
        
        self.previous_enemy_heroes = set(state_manager_instance.enemy_heroes)  # Update for next iteration

class StateLogger:
    """Logs game state at regular intervals to avoid excessive logging."""
    
    def __init__(self):
        """Initialize the state logger."""
        self.last_log_time = 0
        self.log_interval = GSI_LOG_INTERVAL  # Seconds between logs
    
    def should_log(self):
        """Check if enough time has passed to log again."""
        current_time = time.time()
        if current_time - self.last_log_time >= self.log_interval:
            self.last_log_time = current_time
            return True
        return False
    
    def log_state(self, state):
        """Log the current state if the interval has passed."""
        if self.should_log():
            # Log a summary of the state
            hero_name = state.get("hero", {}).get("name", "Unknown")
            game_time = state.get("map", {}).get("game_time", 0)
            logger.info(f"Game state updated: Hero={hero_name}, Game time={game_time}")

class StateManager:
    """Manages the game state, including loading, saving, and updating."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.state = {}
        self.state_file = STATE_FILE_PATH
        self.logger = StateLogger()
        self.hero_extractor = HeroExtractor()
        self._lock = Lock()
        
        # Hero tracking
        self.ally_heroes: Set[str] = set()
        self.enemy_heroes: Set[str] = set()
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
                    self.ally_heroes = set()
                    self.enemy_heroes = set()
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
                
                # Add hero lists to the state
                self.state["allies"] = list(self.ally_heroes)
                self.state["enemies"] = list(self.enemy_heroes)
                
                # Add timestamp
                self.state["_meta"] = {
                    "last_updated": datetime.now().isoformat(),
                    "match_id": self.current_match_id,
                    "heroes_tracked": self.heroes_tracked
                }
                
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
                
                # Restore hero tracking state
                self.ally_heroes = set(self.state.get("allies", []))
                self.enemy_heroes = set(self.state.get("enemies", []))
                meta = self.state.get("_meta", {})
                self.current_match_id = meta.get("match_id")
                self.heroes_tracked = meta.get("heroes_tracked", False)
                
                logger.info(f"Loaded game state from {self.state_file}")
                if self.heroes_tracked:
                    logger.info(f"Restored hero tracking: Allies={self.ally_heroes}, Enemies={self.enemy_heroes}")
            else:
                logger.info(f"No state file found at {self.state_file}, starting with empty state")
                self.state = {}
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            self.state = {}

# Create a singleton instance
state_manager = StateManager() 