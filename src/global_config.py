import os
import yaml

# Base directory for the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Define all config file paths
CONFIG_FILES = {
    "data": {
        "gsi": os.path.join(BASE_DIR, "src/gsi/gsi_config.yaml"),
    },
    "ui": os.path.join(BASE_DIR, "src/ui/ui_config.yaml")
}

# Global logging configuration
LOGGING_CONFIG = {
    "logs_dir": os.path.join(BASE_DIR, "logs"),
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
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
    """Loads all configuration files and returns a unified configuration dictionary."""
    config = {}
    
    # Load data configurations
    data_config = {}
    for data_type, file_path in CONFIG_FILES["data"].items():
        try:
            data_config[data_type] = load_yaml_config(file_path)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"Warning: Could not load {data_type} configuration: {e}")
            data_config[data_type] = {}
    config["data"] = data_config
    
    # Load UI configuration
    try:
        config["ui"] = load_yaml_config(CONFIG_FILES["ui"])
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Warning: Could not load UI configuration: {e}")
        config["ui"] = {}
    
    return config


# Load the global configuration once at module import time
try:
    GLOBAL_CONFIG = load_global_config()
    
    # Extract commonly used configurations for direct import
    UI_CONFIG = GLOBAL_CONFIG.get("ui", {})
    GSI_CONFIG = GLOBAL_CONFIG.get("data", {}).get("gsi", {})
    
    # Extract specific values for direct import
    CHAINLIT_APP_PATH = UI_CONFIG.get("chainlit", {}).get("app_path", "src/ui/chainlit_app.py")
    CHAINLIT_PORT = UI_CONFIG.get("chainlit", {}).get("port", 8001)
    
    # Auth configuration
    AUTH_CONFIG = UI_CONFIG.get("auth", {})
    AUTH_PORT = AUTH_CONFIG.get("port", 8000)
    AUTH_REDIRECT_URI = AUTH_CONFIG.get("redirect_uri", "http://localhost:8000/callback")
    AUTH_SESSION_MAX_AGE = AUTH_CONFIG.get("session_max_age", 60 * 60 * 24 * 7)  # 1 week default
    AUTH_TOKEN_FILE = AUTH_CONFIG.get("token_file", "data/auth_token.json")
    
    # GSI configuration
    GSI_CONFIG_PATH = GSI_CONFIG.get("dota2", {}).get("gsi_config_path", "gamestate_integration_dotact.cfg")
    STATE_FILE_PATH = GSI_CONFIG.get("state_file", "data/game_state.json")
    
    # Extract GSI server configuration
    GSI_SERVER_CONFIG = GSI_CONFIG.get("server", {})
    GSI_HOST = GSI_SERVER_CONFIG.get("host", "127.0.0.1")
    GSI_PORT = GSI_SERVER_CONFIG.get("port", 8002)
    GSI_LOG_INTERVAL = GSI_SERVER_CONFIG.get("log_interval", 60)
    
except Exception as e:
    print(f"Error loading global configuration: {e}")
    # Provide default values if configuration loading fails
    GLOBAL_CONFIG = {}
    UI_CONFIG = {}
    GSI_CONFIG = {}
    AUTH_CONFIG = {}
    
    # Default values
    CHAINLIT_APP_PATH = "src/ui/chainlit_app.py"
    CHAINLIT_PORT = 8001
    AUTH_PORT = 8000
    AUTH_REDIRECT_URI = "http://localhost:8000/callback"
    AUTH_SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 1 week
    AUTH_TOKEN_FILE = "data/auth_token.json"
    GSI_CONFIG_PATH = "gamestate_integration_dotact.cfg"
    STATE_FILE_PATH = "data/game_state.json"
    GSI_HOST = "127.0.0.1"
    GSI_PORT = 8002
    GSI_LOG_INTERVAL = 60
