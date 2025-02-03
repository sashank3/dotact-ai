import os

# Determine the base directory of the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))

# Define module-specific paths
GSI_CONFIG_DIR = os.path.join(BASE_DIR, "src/data/gsi/config")
GSI_CONFIG_FILE = os.path.join(GSI_CONFIG_DIR, "gsi_config.yaml")

# Path to Dota 2's GSI game integration file
DOTA2_GSI_FILE = os.path.join(
    "C:/Program Files (x86)/Steam/steamapps/common/dota 2 beta/game/dota/cfg/gamestate_integration/gamestate_integration_custom.cfg"
)

# Define global paths
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

# Ensure directories exist (e.g., logs and cache)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
