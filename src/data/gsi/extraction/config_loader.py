import yaml
import os
from src.data.gsi.config.paths import GSI_CONFIG_FILE


def load_config():
    """
    Loads the GSI configuration from the YAML file.
    :return: A dictionary containing the configuration settings.
    """
    if not os.path.exists(GSI_CONFIG_FILE):
        raise FileNotFoundError(f"GSI configuration file not found: {GSI_CONFIG_FILE}")

    try:
        with open(GSI_CONFIG_FILE, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML configuration: {e}")
