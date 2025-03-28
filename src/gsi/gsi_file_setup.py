import logging
import os
from src.config import config


def gsi_file_setup():
    """
    Generates the required GSI configuration file for Dota 2 and copies it to the integration directory.
    Includes additional data fields useful for live analysis.
    """
    try:
        # Get the GSI path directly from config
        gsi_path = config.gsi_path
        
        if not gsi_path:
            logging.error("Cannot setup GSI files: GSI path not found")
            logging.info("If you haven't set up Steam yet, run the installer or create a steam_path.yaml file")
            return False
            
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
        
        return True
        
    except Exception as e:
        logging.error(f"GSI config creation failed: {e}")
        return False