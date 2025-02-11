import os


# Determine the base directory of the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

# Define module-specific paths
ENV_FILE = os.path.join(BASE_DIR, ".env")

