"""File-based state manager for cross-process access"""
import logging
import json
import os
import asyncio
import aiofiles
from typing import Optional, Dict
from threading import Lock
from src.global_config import STATE_FILE_PATH


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

class StateManager:
    """Manages the game state, including loading, saving, and updating."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.state = {}
        self.state_file = STATE_FILE_PATH
        self.hero_extractor = HeroExtractor()
        self._lock = Lock()
        
        # Track match and hero detection status, but not the heroes themselves
        self.current_match_id = None
        self.heroes_tracked = False
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        # Load initial state if available
        asyncio.run(self.load_state())
    
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
                asyncio.create_task(self.save_state())
                
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
    
    async def save_state(self) -> None:
        """Save the current state to the state file asynchronously."""
        try:
            # Use aiofiles for async file writing
            async with aiofiles.open(self.state_file, mode='w') as f:
                state_json = json.dumps(self.state, indent=2)
                await f.write(state_json)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    async def load_state(self) -> None:
        """Load the state from the state file if it exists asynchronously."""
        try:
            if os.path.exists(self.state_file):
                # Use aiofiles for async file reading
                async with aiofiles.open(self.state_file, mode='r') as f:
                    contents = await f.read()
                    if contents:  # Check if file is not empty
                        self.state = json.loads(contents)
                    else:
                        self.state = {}  # Handle empty file case

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