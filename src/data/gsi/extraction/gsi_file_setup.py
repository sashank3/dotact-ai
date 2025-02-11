import logging
import os
from src.config.global_config import GLOBAL_CONFIG


def gsi_file_setup():
    """
    Generates the required GSI configuration file for Dota 2 and copies it to the integration directory.
    Includes additional data fields useful for live analysis.
    """
    try:
        # 🔹 Get the actual file path from the config
        gsi_config_path = GLOBAL_CONFIG["data"]["gsi"]["dota2"]["gsi_config_path"]

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
        "map"           "1"
        "player"        "1"
        "hero"          "1"
        "abilities"     "1"
        "items"         "1"
        "buildings"     "1"
        "draft"         "1"
    }}
}}
"""
        # 🔹 Write to the correct Steam directory
        with open(gsi_config_path, "w") as dota_config_file:
            dota_config_file.write(dota_config_content)

        logging.info(f'GSI configuration successfully written to: {gsi_config_path}')

    except Exception as e:
        logging.error(f"Failed to set up GSI configuration: {e}")
