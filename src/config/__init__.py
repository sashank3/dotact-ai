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

    # UI & Chainlit properties
    @property
    def ui_config(self):
        return self._config.get("ui", {})
    
    @property
    def chainlit_app_path(self):
        return self.ui_config.get("chainlit", {}).get("app_path", "src/ui/chainlit_app.py")
    
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
        return self.auth_config.get("token_file", "data/auth_token.json")
    
    @property
    def fastapi_secret_key(self):
        return self.auth_config.get("fastapi_secret_key", "2uvI1zJnlUzn_pWb5LtyG7FjwcDLeMQrnywSbbzHKUM")
    
    # GSI properties
    @property
    def gsi_config(self):
        return self._config.get("data", {}).get("gsi", {})
    
    @property
    def gsi_config_path(self):
        return self.gsi_config.get("dota2", {}).get("gsi_config_path", "gamestate_integration_dotact.cfg")
    
    @property
    def state_file_path(self):
        return self.gsi_config.get("state_file", "data/game_state.json")
    
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
        return self.aws_config.get("access_key_id", "")
    
    @property
    def aws_secret_access_key(self):
        return self.aws_config.get("secret_access_key", "")
    
    @property
    def aws_region(self):
        return self.aws_config.get("region", "us-east-2")
    
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
        return self.google_oauth_config.get("client_id", "")
    
    @property
    def google_client_secret(self):
        return self.google_oauth_config.get("client_secret", "")
    
    # Logging properties
    @property
    def logging_config(self):
        return {
            "logs_dir": get_logs_path(),
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
        }

# Create a singleton instance of the config manager
config = ConfigManager() 