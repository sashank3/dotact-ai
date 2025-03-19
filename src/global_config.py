import os
import yaml
import logging
import sys

# Import app directory management from our exe module
from src.exe.app_dirs import APP_DIRS, IS_FROZEN

# Configure basic logger
logger = logging.getLogger(__name__)

# Base directory for the project
BASE_DIR = APP_DIRS['app_root']

# Define all config file paths, with fallbacks for executable context
def get_config_files():
    if IS_FROZEN:
        # In executable context, look first in the config directory, then fall back to bundled files
        return {
            "data": {
                "gsi": os.path.join(APP_DIRS['config_dir'], "gsi_config.yaml"),
            },
            "ui": os.path.join(APP_DIRS['config_dir'], "ui_config.yaml"),
            "cloud": os.path.join(APP_DIRS['config_dir'], "cloud_config.yaml"),
            "secrets": os.path.join(APP_DIRS['config_dir'], "secrets_config.yaml")
        }
    else:
        # In development, use the original paths
        return {
            "data": {
                "gsi": os.path.join(BASE_DIR, "src/gsi/gsi_config.yaml"),
            },
            "ui": os.path.join(BASE_DIR, "src/ui/ui_config.yaml"),
            "cloud": os.path.join(BASE_DIR, "src/cloud/cloud_config.yaml"),
            "secrets": os.path.join(BASE_DIR, "src/cloud/secrets_config.yaml")
        }

CONFIG_FILES = get_config_files()

# Global logging configuration
LOGGING_CONFIG = {
    "logs_dir": APP_DIRS['logs_dir'],
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
}

# Modified load_yaml_config to try multiple locations for config files
def load_yaml_config(file_path):
    """Loads a YAML configuration file and returns its content as a dictionary."""
    paths_to_try = [file_path]
    
    # If we're in executable mode, also try the bundled resource path
    if IS_FROZEN:
        # Try to find a default config in the executable directory
        filename = os.path.basename(file_path)
        exe_dir = os.path.dirname(sys.executable)
        bundled_path = os.path.join(exe_dir, "config", filename)
        paths_to_try.append(bundled_path)
    
    # Try each path in order
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, "r") as file:
                    return yaml.safe_load(file) or {}
            except yaml.YAMLError as e:
                logger.warning(f"Error parsing YAML configuration at {path}: {e}")
    
    # If we get here, none of the paths worked
    logger.warning(f"Configuration file not found at any of these locations: {paths_to_try}")
    return {}  # Return empty dict as fallback

def load_global_config():
    """Loads all configuration files and returns a unified configuration dictionary."""
    config = {}
    
    # Load data configurations
    data_config = {}
    for data_type, file_path in CONFIG_FILES["data"].items():
        try:
            data_config[data_type] = load_yaml_config(file_path)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Could not load {data_type} configuration: {e}")
            data_config[data_type] = {}
    config["data"] = data_config
    
    # Load UI configuration
    try:
        config["ui"] = load_yaml_config(CONFIG_FILES["ui"])
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Could not load UI configuration: {e}")
        config["ui"] = {}
    
    # Load Cloud configuration
    try:
        config["cloud"] = load_yaml_config(CONFIG_FILES["cloud"])
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Could not load Cloud configuration: {e}")
        config["cloud"] = {}
    
    # Load Secrets configuration
    try:
        config["secrets"] = load_yaml_config(CONFIG_FILES["secrets"])
        logger.info("Successfully loaded secrets configuration")
    except FileNotFoundError:
        logger.warning(f"Secrets configuration file not found: {CONFIG_FILES['secrets']}")
        config["secrets"] = {}
    except RuntimeError as e:
        logger.warning(f"Error parsing secrets configuration: {e}")
        config["secrets"] = {}
    except Exception as e:
        logger.warning(f"Unexpected error loading secrets configuration: {str(e)}")
        config["secrets"] = {}
    
    return config


# Load the global configuration once at module import time
try:
    GLOBAL_CONFIG = load_global_config()
    
    # Extract commonly used configurations for direct import
    UI_CONFIG = GLOBAL_CONFIG.get("ui", {})
    GSI_CONFIG = GLOBAL_CONFIG.get("data", {}).get("gsi", {})
    CLOUD_CONFIG = GLOBAL_CONFIG.get("cloud", {})
    SECRETS_CONFIG = GLOBAL_CONFIG.get("secrets", {})

    # Extract specific values for direct import
    CHAINLIT_APP_PATH = UI_CONFIG.get("chainlit", {}).get("app_path", "src/ui/chainlit_app.py")
    CHAINLIT_PORT = UI_CONFIG.get("chainlit", {}).get("port", 8001)
    
    # Auth configuration
    AUTH_CONFIG = UI_CONFIG.get("auth", {})
    AUTH_PORT = AUTH_CONFIG.get("port", 8000)
    AUTH_REDIRECT_URI = AUTH_CONFIG.get("redirect_uri", "http://localhost:8000/callback")
    AUTH_SESSION_MAX_AGE = AUTH_CONFIG.get("session_max_age", 60 * 60 * 24 * 7)  # 1 week default
    AUTH_TOKEN_FILE = AUTH_CONFIG.get("token_file", "data/auth_token.json")
    FASTAPI_SECRET_KEY = AUTH_CONFIG.get("fastapi_secret_key", "2uvI1zJnlUzn_pWb5LtyG7FjwcDLeMQrnywSbbzHKUM")
    
    # GSI configuration
    GSI_CONFIG_PATH = GSI_CONFIG.get("dota2", {}).get("gsi_config_path", "gamestate_integration_dotact.cfg")
    STATE_FILE_PATH = GSI_CONFIG.get("state_file", "data/game_state.json")
    
    # Extract GSI server configuration
    GSI_SERVER_CONFIG = GSI_CONFIG.get("server", {})
    GSI_HOST = GSI_SERVER_CONFIG.get("host", "127.0.0.1")
    GSI_PORT = GSI_SERVER_CONFIG.get("port", 8002)
    
    # Extract AWS configuration
    AWS_CONFIG = SECRETS_CONFIG.get("aws", {})
    AWS_ACCESS_KEY_ID = AWS_CONFIG.get("access_key_id", "")
    AWS_SECRET_ACCESS_KEY = AWS_CONFIG.get("secret_access_key", "")
    AWS_REGION = AWS_CONFIG.get("region", "us-east-2")
    
    # Extract Lambda configuration
    LAMBDA_CONFIG = CLOUD_CONFIG.get("lambda", {})
    PROCESS_QUERY_FUNCTION_ARN = LAMBDA_CONFIG.get("process_query_arn", "")
    CHECK_ACCESS_FUNCTION_ARN = LAMBDA_CONFIG.get("check_access_arn", "")
    
    # Extract Cognito configuration
    COGNITO_CONFIG = CLOUD_CONFIG.get("cognito", {})
    COGNITO_USER_POOL_ID = COGNITO_CONFIG.get("user_pool_id", "")
    COGNITO_CLIENT_ID = COGNITO_CONFIG.get("client_id", "")
    COGNITO_DOMAIN = COGNITO_CONFIG.get("domain", "")
    
    # Extract API Gateway configuration
    API_GATEWAY_CONFIG = CLOUD_CONFIG.get("api_gateway", {})
    API_GATEWAY_ID = API_GATEWAY_CONFIG.get("id", "")
    API_ROOT_RESOURCE_ID = API_GATEWAY_CONFIG.get("root_resource_id", "")
    PROCESS_QUERY_API_URL = API_GATEWAY_CONFIG.get("process_query_url", "")
    API_BASE_URL = API_GATEWAY_CONFIG.get("base_url", "")
    
    # Extract Google OAuth configuration
    GOOGLE_OAUTH_CONFIG = SECRETS_CONFIG.get("google_oauth", {})
    GOOGLE_CLIENT_ID = GOOGLE_OAUTH_CONFIG.get("client_id", "")
    GOOGLE_CLIENT_SECRET = GOOGLE_OAUTH_CONFIG.get("client_secret", "")
    
    logger.info("Global configuration loaded successfully")
    
except Exception as e:
    logger.error(f"Error loading global configuration: {e}")
    # Provide default values if configuration loading fails
    GLOBAL_CONFIG = {}
    UI_CONFIG = {}
    GSI_CONFIG = {}
    AUTH_CONFIG = {}
    CLOUD_CONFIG = {}
    SECRETS_CONFIG = {}
    
    # Default values
    CHAINLIT_APP_PATH = "src/ui/chainlit_app.py"
    CHAINLIT_PORT = 8001
    AUTH_PORT = 8000
    AUTH_REDIRECT_URI = "http://localhost:8000/callback"
    AUTH_SESSION_MAX_AGE = 60 * 60 * 24 * 2 # 1 day
    AUTH_TOKEN_FILE = "data/auth_token.json"
    FASTAPI_SECRET_KEY = "2uvI1zJnlUzn_pWb5LtyG7FjwcDLeMQrnywSbbzHKUM"
    GSI_CONFIG_PATH = "gamestate_integration_keenmind.cfg"
    STATE_FILE_PATH = "data/game_state.json"
    GSI_HOST = "127.0.0.1"
    GSI_PORT = 8002
    
    # AWS defaults
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""
    AWS_REGION = "us-east-2"
    PROCESS_QUERY_FUNCTION_ARN = ""
    CHECK_ACCESS_FUNCTION_ARN = ""
    
    # Cognito defaults
    COGNITO_USER_POOL_ID = ""
    COGNITO_CLIENT_ID = ""
    COGNITO_DOMAIN = ""
    
    # API Gateway defaults
    API_GATEWAY_ID = ""
    API_ROOT_RESOURCE_ID = ""
    PROCESS_QUERY_API_URL = ""
    API_BASE_URL = ""
    
    # Google OAuth defaults
    GOOGLE_CLIENT_ID = ""
    GOOGLE_CLIENT_SECRET = ""

# Ensure these directories exist
os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(AUTH_TOKEN_FILE), exist_ok=True)

# Update data file paths to use APP_DIRS
STATE_FILE_PATH = os.path.join(APP_DIRS['data_dir'], "game_state.json")
AUTH_TOKEN_FILE = os.path.join(APP_DIRS['data_dir'], "auth_token.json")
