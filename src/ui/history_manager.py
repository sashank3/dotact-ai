"""
History manager for storing and retrieving chat history for Keenmind.
This module handles saving and loading chat history for users.
"""
import os
import json
import logging
import datetime
import sys
from pathlib import Path

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import STATE_FILE_PATH

# Configure logging
logger = logging.getLogger(__name__)

# Constants
HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "chat_history")

def save_chat_history(user_id: str, query: str, response: str) -> None:
    """
    Save a chat entry to the user's chat history.
    
    Args:
        user_id: The user's ID (email)
        query: The user's query
        response: The response from the system
    """
    try:
        # Create history directory if it doesn't exist
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        # Create user directory if it doesn't exist
        user_dir = os.path.join(HISTORY_DIR, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Get current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Load game state at the time of the query
        game_state = {}
        if os.path.exists(STATE_FILE_PATH) and os.path.getsize(STATE_FILE_PATH) > 0:
            try:
                with open(STATE_FILE_PATH, "r") as f:
                    game_state = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing game state file: {str(e)}")
        
        # Create chat entry
        chat_entry = {
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "game_state": game_state
        }
        
        # Save chat entry to a file
        # Use timestamp in filename to ensure uniqueness
        filename = f"{timestamp.replace(':', '-')}.json"
        filepath = os.path.join(user_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(chat_entry, f, indent=2)
        
        # Also save to a consolidated history file
        history_file = os.path.join(user_dir, "history.json")
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []
        
        # Add new entry (without full game state to keep file size manageable)
        history_entry = {
            "timestamp": timestamp,
            "query": query,
            "response": response
        }
        history.append(history_entry)
        
        # Save updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Saved chat history entry for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error saving chat history: {str(e)}")

def load_chat_history(user_id: str) -> list:
    """
    Load the chat history for a user.
    
    Args:
        user_id: The user's ID (email)
        
    Returns:
        A list of chat entries
    """
    try:
        # Check if user directory exists
        user_dir = os.path.join(HISTORY_DIR, user_id)
        if not os.path.exists(user_dir):
            logger.info(f"No chat history found for user {user_id}")
            return []
        
        # Load consolidated history file
        history_file = os.path.join(user_dir, "history.json")
        if not os.path.exists(history_file):
            logger.info(f"No history file found for user {user_id}")
            return []
        
        with open(history_file, "r") as f:
            history = json.load(f)
        
        logger.info(f"Loaded {len(history)} chat history entries for user {user_id}")
        return history
        
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}")
        return []

def get_detailed_chat_entry(user_id: str, timestamp: str) -> dict:
    """
    Get a detailed chat entry including game state.
    
    Args:
        user_id: The user's ID (email)
        timestamp: The timestamp of the entry
        
    Returns:
        The detailed chat entry or None if not found
    """
    try:
        # Format timestamp for filename
        filename = f"{timestamp.replace(':', '-')}.json"
        filepath = os.path.join(HISTORY_DIR, user_id, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Detailed chat entry not found: {filepath}")
            return None
        
        with open(filepath, "r") as f:
            entry = json.load(f)
        
        logger.info(f"Loaded detailed chat entry for user {user_id} at {timestamp}")
        return entry
        
    except Exception as e:
        logger.error(f"Error loading detailed chat entry: {str(e)}")
        return None

def clear_chat_history(user_id: str) -> bool:
    """
    Clear the chat history for a user.
    
    Args:
        user_id: The user's ID (email)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if user directory exists
        user_dir = os.path.join(HISTORY_DIR, user_id)
        if not os.path.exists(user_dir):
            logger.info(f"No chat history found for user {user_id}")
            return True
        
        # Delete all files in the user directory
        for file in os.listdir(user_dir):
            os.remove(os.path.join(user_dir, file))
        
        logger.info(f"Cleared chat history for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return False
