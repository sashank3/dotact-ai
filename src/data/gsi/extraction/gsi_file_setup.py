import logging
import os
from src.data.gsi.config.paths import DOTA2_GSI_FILE
from src.data.gsi.extraction.config_loader import load_config


def gsi_file_setup():
    """
    Generates the required GSI configuration file for Dota 2 and copies it to the integration directory.
    Includes additional data fields useful for live analysis.
    """
    try:
        config = load_config()
        os.makedirs(os.path.dirname(DOTA2_GSI_FILE), exist_ok=True)  # Ensure directory exists

        dota_config_content = f"""
"Dota 2 Integration Configuration"
{{
    "uri"           "http://{config['server']['host']}:{config['server']['port']}/"
    "timeout"       "5.0"
    "heartbeat"     "30.0"
    "auth"
    {{
        "token"      "{config['auth']['token']}"
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
        with open(DOTA2_GSI_FILE, "w") as dota_config_file:
            dota_config_file.write(dota_config_content)
        logging.info(f"GSI configuration successfully written to: {DOTA2_GSI_FILE}")

    except Exception as e:
        logging.error(f"Failed to set up GSI configuration: {e}")
