import subprocess
import logging
from src.logger.logger import setup_logging
import os
from src.global_config import GLOBAL_CONFIG, BASE_DIR


def start_ui():
    setup_logging(log_file="ui_module.log")
    logging.info("[UI ORCHESTRATOR] Launching Chainlit UI...")

    # Get path from config
    rel_path = GLOBAL_CONFIG["ui"]["chainlit"]["app_path"]
    chainlit_app_path = os.path.join(BASE_DIR, rel_path)
    
    logging.debug(f"Chainlit app path: {chainlit_app_path}")
    subprocess.run([
        "chainlit", "run", chainlit_app_path,
        "--config", os.path.join(BASE_DIR, ".chainlit/config.toml"),
        "--no-watch"
    ])
