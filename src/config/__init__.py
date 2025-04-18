"""
Configuration module that loads settings from YAML files in the root/config directory.
This module supports both development and production environments and provides 
convenient access to configuration values via properties.
"""
import os
import yaml
import logging
from src.utils.paths import get_config_path, get_logs_path

# Configure module logger
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration manager that provides property access 
    to configuration values with appropriate defaults.
    """
    def __init__(self):
        # Initialize the configuration dictionary
        self._config = self._load_global_config()
        
    def _load_yaml_config(self, file_path):
        """Loads a YAML configuration file and returns its content as a dictionary."""
        if not os.path.exists(file_path):
            logger.warning(f"Configuration file not found: {file_path}")
            return {}

        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading config file {file_path}: {str(e)}")
            return {}

    def _load_global_config(self):
        """
        Loads all configuration files from the config directory.
        Maintains the same structure as the original global_config.py.
        """
        config = {}
        config_dir = get_config_path()
        logger.info(f"Loading configurations from: {config_dir}")
        
        # Define config file paths
        config_files = {
            "gsi": os.path.join(config_dir, "gsi_config.yaml"),
            "ui": os.path.join(config_dir, "ui_config.yaml"),
            "cloud": os.path.join(config_dir, "cloud_config.yaml"),
            "secrets": os.path.join(config_dir, "secrets_config.yaml")
        }
        
        # Load GSI configuration (nested under data like in original global_config)
        data_config = {}
        gsi_config = self._load_yaml_config(config_files["gsi"])
        data_config["gsi"] = gsi_config
        config["data"] = data_config
        
        # Load UI configuration
        config["ui"] = self._load_yaml_config(config_files["ui"])
        
        # Load Cloud configuration
        config["cloud"] = self._load_yaml_config(config_files["cloud"])
        
        # Load Secrets configuration
        config["secrets"] = self._load_yaml_config(config_files["secrets"])
        
        logger.info(f"Loaded configurations: {list(config.keys())}")
        return config
    
    def get(self, *keys, default=None):
        """
        Get a configuration value by navigating through nested dictionaries.
        
        Args:
            *keys: A sequence of keys to navigate the nested dictionaries
            default: Value to return if the path doesn't exist
            
        Example:
            config.get("ui", "auth", "port", default=8000)
        """
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _get_embedded_credential(self, key):
        """Get a credential from embedded credentials module."""
        try:
            import importlib
            embedded = importlib.import_module('src.config.embedded_credentials')
            return getattr(embedded, key)
        except (ImportError, AttributeError):
            logger.error(f"Failed to load embedded credential '{key}': {e}")
            return None

    # UI & Chainlit properties
    @property
    def ui_config(self):
        return self._config.get("ui", {})
    
    @property
    def chainlit_app_path(self):
        return self.ui_config.get("chainlit", {}).get("app_path", "src/ui/chainlit_app.py")
    
    @property
    def chainlit_tray_icon_path(self):
        return self.ui_config.get("chainlit", {}).get("icon_path", "public/favicon.py")
    
    @property
    def chainlit_port(self):
        return self.ui_config.get("chainlit", {}).get("port", 8001)
    
    # Auth properties
    @property
    def auth_config(self):
        return self.ui_config.get("auth", {})
    
    @property
    def auth_port(self):
        return self.auth_config.get("port", 8000)
    
    @property
    def auth_redirect_uri(self):
        return self.auth_config.get("redirect_uri", "http://localhost:8000/callback")
    
    @property
    def auth_session_max_age(self):
        return self.auth_config.get("session_max_age", 60 * 60 * 24 * 7)  # 1 week default
    
    @property
    def auth_token_file(self):
        # Get the configured path from the config
        config_path = self.auth_config.get("token_file", "data/auth_token.json")
        
        # If we're in a frozen environment (production), we need to use the user data path
        from src.bootstrap import is_frozen
        from src.utils.paths import get_user_data_path
        
        if is_frozen():
            # For a frozen app, return an absolute path in the user data directory
            # Just take the filename part from the config path
            filename = os.path.basename(config_path)
            return os.path.join(get_user_data_path(), filename)
        else:
            # In development, use the path from the config as is
            return config_path
    
    @property
    def fastapi_secret_key(self):
        return self.auth_config.get("fastapi_secret_key", "2uvI1zJnlUzn_pWb5LtyG7FjwcDLeMQrnywSbbzHKUM")
    
    # GSI properties
    @property
    def gsi_config(self):
        return self._config.get("data", {}).get("gsi", {})
    
    @property
    def gsi_path(self):
        """Get the actual path where the GSI configuration file should be placed"""
        from src.bootstrap import is_frozen, get_application_root
        import os
        from src.utils.paths import read_steam_path_config
        
        if is_frozen():
            # In production, read from steam_path.yaml to get the actual GSI path
            app_root = get_application_root()
            steam_config_path = os.path.join(app_root, 'steam_path.yaml')
            
            if os.path.exists(steam_config_path):
                steam_config = read_steam_path_config(steam_config_path)
                if steam_config and 'steam' in steam_config and 'gsi_path' in steam_config['steam']:
                    # Combine the directory with the filename
                    gsi_dir = steam_config['steam']['gsi_path']
                    return os.path.join(gsi_dir, "gamestate_integration_dotact.cfg")
            
            logger.warning("GSI path not found in frozen application")
            return None
        else:
            # In development, also return the full path
            from src.utils.paths import get_config_path
            config_dir = get_config_path()
            return os.path.join(config_dir, self.gsi_config.get("dota2", {}).get("gsi_config_path", "gamestate_integration_dotact.cfg"))
    
    @property
    def state_file_path(self):
        # Get the configured path from the YAML config
        config_path = self.gsi_config.get("state_file", "data/game_state.json")
        
        # If we're in a frozen environment (production), we need to use the user data path
        from src.bootstrap import is_frozen
        from src.utils.paths import get_user_data_path
        
        if is_frozen():
            # For a frozen app, return an absolute path in the user data directory
            # Just take the filename part from the config path
            filename = os.path.basename(config_path)
            return os.path.join(get_user_data_path(), filename)
        else:
            # In development, use the path from the config as is
            return config_path
    
    @property
    def gsi_server_config(self):
        return self.gsi_config.get("server", {})
    
    @property
    def gsi_host(self):
        return self.gsi_server_config.get("host", "127.0.0.1")
    
    @property
    def gsi_port(self):
        return self.gsi_server_config.get("port", 8002)
    
    @property
    def gsi_auth_token(self):
        return self.gsi_config.get("auth", {}).get("token", "my_super_secret_token_123!")
    
    @property
    def gsi_first_install(self):
        return self.gsi_config.get("dota2", {}).get("first_install", True)
    
    # AWS properties
    @property
    def aws_config(self):
        return self._config.get("secrets", {}).get("aws", {})

    @property
    def aws_access_key_id(self):
        from src.bootstrap import is_frozen
        if is_frozen():
            return self._get_embedded_credential('AWS_ACCESS_KEY_ID') or ""
        return self.aws_config.get('access_key_id', "")

    @property
    def aws_secret_access_key(self):
        from src.bootstrap import is_frozen
        if is_frozen():
            return self._get_embedded_credential('AWS_SECRET_ACCESS_KEY') or ""
        return self.aws_config.get('secret_access_key', "")

    @property
    def aws_region(self):
        from src.bootstrap import is_frozen
        if is_frozen():
            return self._get_embedded_credential('AWS_REGION') or "us-east-2"
        return self.aws_config.get('region', "us-east-2")
    
    # Lambda properties
    @property
    def lambda_config(self):
        return self._config.get("cloud", {}).get("lambda", {})
    
    @property
    def process_query_function_arn(self):
        return self.lambda_config.get("process_query_arn", "")
    
    @property
    def check_access_function_arn(self):
        return self.lambda_config.get("check_access_arn", "")
    
    # Cognito properties
    @property
    def cognito_config(self):
        return self._config.get("cloud", {}).get("cognito", {})
    
    @property
    def cognito_user_pool_id(self):
        return self.cognito_config.get("user_pool_id", "")
    
    @property
    def cognito_client_id(self):
        return self.cognito_config.get("client_id", "")
    
    @property
    def cognito_domain(self):
        return self.cognito_config.get("domain", "")
    
    # API Gateway properties
    @property
    def api_gateway_config(self):
        return self._config.get("cloud", {}).get("api_gateway", {})
    
    @property
    def api_gateway_id(self):
        return self.api_gateway_config.get("id", "")
    
    @property
    def api_root_resource_id(self):
        return self.api_gateway_config.get("root_resource_id", "")
    
    @property
    def process_query_api_url(self):
        return self.api_gateway_config.get("process_query_url", "")
    
    @property
    def api_base_url(self):
        return self.api_gateway_config.get("base_url", "")
    
    # Google OAuth properties
    @property
    def google_oauth_config(self):
        return self._config.get("secrets", {}).get("google_oauth", {})
    
    @property
    def google_client_id(self):
        from src.bootstrap import is_frozen
        if is_frozen():
            return self._get_embedded_credential('GOOGLE_CLIENT_ID') or ""
        return self.google_oauth_config.get('client_id', "")
    
    @property
    def google_client_secret(self):
        from src.bootstrap import is_frozen
        if is_frozen():
            return self._get_embedded_credential('GOOGLE_CLIENT_SECRET') or ""
        return self.google_oauth_config.get('client_secret', "")
    
    # Logging properties
    @property
    def logging_config(self):
        return {
            "logs_dir": get_logs_path(),
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
        }
    
    @property
    def uvicorn_log_config(self):
        """
        Provides a logging configuration dictionary for Uvicorn,
        compatible with --windowed mode and designed to propagate
        logs to the root logger (handled by LogManager).
        Uses standard logging.Formatter which does not accept 'use_colors'.
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "logging.Formatter", # Use standard Python Formatter
                    "fmt": self.logging_config.get("format", "%(levelname)s:%(name)s:%(message)s"),
                    "datefmt": "%Y-%m-%d %H:%M:%S", # Optional: match your date format
                    # 'validate': False # Add if needed, but usually not required for basic format strings
                },
                "access": {
                    "()": "logging.Formatter", # Use standard Python Formatter
                    "fmt": self.logging_config.get("format", "%(levelname)s:%(name)s:%(message)s"), # Or specific access fmt
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    # 'validate': False
                },
            },
            "handlers": {
                 # Still no handlers needed here; rely on propagation
            },
            "loggers": {
                "uvicorn": {
                    "handlers": [],
                    "level": "INFO",
                    "propagate": True,
                },
                "uvicorn.error": {
                    "handlers": [],
                    "level": "INFO",
                    "propagate": True,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "INFO", # Adjust level as needed
                    "propagate": True,
                },
            },
        }

# Create a singleton instance of the config manager
config = ConfigManager()