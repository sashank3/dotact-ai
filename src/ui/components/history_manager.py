import json
import logging
import os
from src.logger.log_manager import log_manager

def save_chat_history(chat_entry: dict) -> None:
    """Save a chat entry to the session's chat history file."""
    history_file = log_manager.get_chat_history_path()
    try:
        # Ensure directory exists
        history_dir = os.path.dirname(history_file)
        os.makedirs(history_dir, exist_ok=True)
        
        # Load existing history
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = []
        
        # Add new entry
        history.append(chat_entry)
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        logging.debug(f"[HISTORY MANAGER] Saved chat entry to {history_file}")
    except Exception as e:
        logging.error(f"[HISTORY MANAGER] Error saving chat history: {e}")
        logging.error(f"[HISTORY MANAGER] Path attempted: {history_file}")

def load_chat_history() -> list:
    """Load chat history from the session's history file."""
    history_file = log_manager.get_chat_history_path()
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
        logging.debug(f"[HISTORY MANAGER] Loaded {len(history)} entries from {history_file}")
        return history
    except (FileNotFoundError, json.JSONDecodeError):
        logging.info("[HISTORY MANAGER] No existing chat history found, starting fresh")
        return []
