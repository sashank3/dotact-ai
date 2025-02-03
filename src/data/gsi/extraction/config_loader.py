import yaml
from src.data.gsi.config.paths import GSI_CONFIG_FILE


def load_config():
    """
    Loads the GSI configuration from the YAML file.
    :return: A dictionary containing the configuration settings.
    """
    with open(GSI_CONFIG_FILE, "r") as file:
        return yaml.safe_load(file)
