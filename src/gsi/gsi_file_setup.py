import logging
import os
import yaml
from src.config import config
from src.utils.paths import get_config_path, get_steam_path_config

def gsi_file_setup():
    """
    Generates the required GSI configuration file for Dota 2 and copies it to the integration directory.
    Includes additional data fields useful for live analysis.
    """
    try:
        # Get the Steam path configuration
        steam_config_path = get_steam_path_config()
        
        if not steam_config_path:
            logging.error("Cannot setup GSI files: Steam path configuration not found")
            logging.info("If you haven't set up Steam yet, run the installer or create a steam_path.yaml file")
            return False
            
        # Load the Steam configuration
        try:
            with open(steam_config_path, 'r') as file:
                steam_config = yaml.safe_load(file)
        except Exception as e:
            logging.error(f"Failed to read Steam configuration file: {e}")
            return False
            
        # Get paths from the config
        gsi_path = steam_config.get('steam', {}).get('gsi_path')
        
        if not gsi_path:
            logging.error("Invalid Steam path configuration: 'gsi_path' not found")
            return False
        
        # Check if first_install flag is set to False - if so, we've already done the setup before
        first_install = steam_config.get('steam', {}).get('first_install', True)
        if not first_install:
            logging.info("GSI files already set up in a previous run")
            return True
            
        # Ensure GSI directory exists
        try:
            os.makedirs(os.path.dirname(gsi_path), exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create GSI directory: {e}")
            logging.info("This may happen if Steam is installed in a protected location. Try running as administrator.")
            return False
            
        # Generate GSI config content
        dota_config_content = f"""
"Dota 2 Integration Configuration"
{{
    "uri"           "http://{config.gsi_host}:{config.gsi_port}/"
    "timeout"       "5.0"
    "heartbeat"     "30.0"
    "auth"
    {{
        "token"      "{config.gsi_auth_token}"
    }}
    "data"
    {{
        "provider"      "1"
        "map"           "1"
        "player"        "1"
        "hero"          "1"
        "abilities"     "1"
        "items"         "1"
        "buildings"     "1"
        "draft"         "1"
        "minimap"       "1"
    }}
}}
"""
        # Write to the correct Steam directory
        try:
            with open(gsi_path, "w") as dota_config_file:
                dota_config_file.write(dota_config_content)
            logging.info(f"GSI config created successfully")
        except PermissionError:
            logging.error("Cannot write to Steam directory. Please run the application as administrator.")
            return False
        
        # Update the first_install flag
        try:
            update_first_install_flag()
        except PermissionError:
            logging.error("Cannot update installation flag. Please run the application as administrator.")
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"GSI config creation failed: {e}")
        return False

def update_first_install_flag():
    """
    Updates the first_install flag in the steam_path.yaml file.
    """
    try:
        # Get the steam_path.yaml location
        steam_config_path = get_steam_path_config()
        
        if not steam_config_path:
            logging.error("Cannot update first_install flag: Steam path configuration not found")
            return
            
        # Load the current configuration
        with open(steam_config_path, 'r') as file:
            steam_config = yaml.safe_load(file)
        
        # Update the first_install flag
        if 'steam' not in steam_config:
            steam_config['steam'] = {}
        
        steam_config['steam']['first_install'] = False
        
        # Write the updated configuration back
        with open(steam_config_path, 'w') as file:
            yaml.dump(steam_config, file, default_flow_style=False)
        
        logging.info("Updated first_install flag to False in steam_path.yaml")
    except Exception as e:
        logging.error(f"Failed to update first_install flag: {e}")
        raise  # Re-raise to allow the calling function to handle it 