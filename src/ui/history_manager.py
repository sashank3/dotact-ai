"""
History manager for storing and retrieving chat history for Keenplay.
This module handles saving and loading chat history for users.
"""
import os
import json
import logging
import datetime
import sys

# Simple, reliable path handling
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    # Running in development environment
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, root_dir)

# Import configuration
from src.config import config
from src.logger.log_manager import log_manager

# Configure logging
logger = logging.getLogger(__name__)

def save_chat_history(user_id: str, query: str, response: str, game_state: dict, thinking_content: str = "") -> None:
    """
    Save a chat entry to the session's chat history.
    
    Args:
        user_id: The user's ID (email)
        query: The user's query
        response: The response from the system
        game_state: The game state dictionary at the time of the query
        thinking_content: The thinking/reasoning content from the LLM (optional)
    """
    try:
        # Get the current session directory from log_manager
        session_dir = log_manager.session_dir
        
        # Create chat history file path in the session directory
        chat_history_file = os.path.join(session_dir, "chat_history.json")
        
        # Get current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Create chat entry using the game_state passed as an argument
        chat_entry = {
            "timestamp": timestamp,
            "user_id": user_id,
            "query": query,
            "response": response,
            "thinking_content": thinking_content,
            # "game_state": game_state
        }
        
        # Load existing history or create new one
        history = []
        if os.path.exists(chat_history_file):
            try:
                with open(chat_history_file, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse existing chat history file. Creating new one.")
                history = []
        
        # Add new entry
        history.append(chat_entry)
        
        # Save updated history
        with open(chat_history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Saved chat history entry for user {user_id} in session directory")
        
    except Exception as e:
        logger.error(f"Error saving chat history: {str(e)}")
