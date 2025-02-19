import os
import yaml

# Base directory for the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Define all config file paths
CONFIG_FILES = {
    "data": {
        "gsi": os.path.join(BASE_DIR, "src/data/gsi/gsi_config.yaml"),
    },
    "llm": os.path.join(BASE_DIR, "src/llm/llm_config.yaml"),
}


def load_yaml_config(file_path):
    """Loads a YAML configuration file and returns its content as a dictionary."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file) or {}  # Ensure an empty dict if the file is empty
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML configuration: {e}")


def load_global_config():
    """
    Loads all configurations from different modules into a global dictionary.
    """
    global_config = {}

    for category, config in CONFIG_FILES.items():
        if isinstance(config, dict):  # Nested configs (like "data")
            global_config[category] = {name: load_yaml_config(path) for name, path in config.items()}
        else:  # Direct config file (like "llm")
            global_config[category] = load_yaml_config(config)

    return global_config


# Global variable that holds the config once loaded
GLOBAL_CONFIG = load_global_config()
