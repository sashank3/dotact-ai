import json
import os

HISTORY_FILE = "chat_history.json"


def save_chat_history(chat_entry):
    """Appends a new chat entry to the history file."""
    history = load_chat_history()
    history.append(chat_entry)

    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)


def load_chat_history():
    """Loads past chat history from file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    return []
