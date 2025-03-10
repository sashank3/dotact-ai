import logging
import os
import yaml
from src.global_config import GLOBAL_CONFIG, CONFIG_FILES

def gsi_file_setup():
    """
    Generates the required GSI configuration file for Dota 2 and copies it to the integration directory.
    Includes additional data fields useful for live analysis.
    """
    try:
        # 🔹 Get the actual file path from the config
        gsi_config_path = GLOBAL_CONFIG["data"]["gsi"]["dota2"]["gsi_config_path"]
        logging.info(f"Creating GSI config at: {gsi_config_path}")

        # 🔹 Ensure the directory exists
        os.makedirs(os.path.dirname(gsi_config_path), exist_ok=True)

        # 🔹 Generate GSI config content
        dota_config_content = f"""
"Dota 2 Integration Configuration"
{{
    "uri"           "http://{GLOBAL_CONFIG["data"]["gsi"]['server']['host']}:{GLOBAL_CONFIG["data"]["gsi"]['server']['port']}/"
    "timeout"       "5.0"
    "heartbeat"     "30.0"
    "auth"
    {{
        "token"      "{GLOBAL_CONFIG["data"]["gsi"]['auth']['token']}"
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
        # 🔹 Write to the correct Steam directory
        with open(gsi_config_path, "w") as dota_config_file:
            dota_config_file.write(dota_config_content)

        logging.info(f"GSI config created successfully")
        
        # 🔹 Update the first_install flag to False
        update_first_install_flag()
        
    except Exception as e:
        logging.error(f"GSI config creation failed: {e}")
        raise  # Add this to see the error

def update_first_install_flag():
    """
    Updates the first_install flag in the GSI config YAML to False
    after the first successful installation.
    """
    try:
        gsi_config_path = CONFIG_FILES["data"]["gsi"]
        
        # Read the current config
        with open(gsi_config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Update the flag
        config["dota2"]["first_install"] = False
        
        # Write the updated config back to the file
        with open(gsi_config_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False)
        
        logging.info("Updated first_install flag to False")
    except Exception as e:
        logging.error(f"Failed to update first_install flag: {e}") 