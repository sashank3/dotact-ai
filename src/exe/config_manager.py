import os
import yaml
import logging
import shutil
from .app_dirs import APP_DIRS, IS_FROZEN

logger = logging.getLogger(__name__)

def load_config(config_name, default_config=None):
    """
    Load a configuration file with fallback mechanisms.
    
    Args:
        config_name: Name of the config file (e.g., 'gsi.yaml')
        default_config: Optional dictionary with default values
        
    Returns:
        Config dict loaded from file, or default_config if file not found
    """
    config_paths = get_config_paths(config_name)
    
    # Try each path in order of preference
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded config from {path}")
                return config or {}
            except Exception as e:
                logger.warning(f"Error loading config from {path}: {str(e)}")
    
    # If we get here, no config file was found/loaded
    logger.warning(f"No config file found for '{config_name}'. Using defaults.")
    return default_config if default_config is not None else {}

def save_config(config_name, config_data):
    """
    Save configuration to the user's config directory.
    
    Args:
        config_name: Name of the config file
        config_data: Dictionary of configuration data to save
        
    Returns:
        Path to the saved config file or None if save failed
    """
    # Always save to user config directory
    config_path = os.path.join(APP_DIRS['config_dir'], config_name)
    
    # Make sure directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        logger.info(f"Saved config to {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Failed to save config {config_name}: {str(e)}")
        return None

def get_config_paths(config_name):
    """
    Get all possible paths for a config file in order of preference.
    
    Args:
        config_name: Name of the config file
        
    Returns:
        List of possible config file paths in order of preference
    """
    if IS_FROZEN:
        # In executable mode, preference order:
        # 1. User config directory
        # 2. Bundled configs
        return [
            os.path.join(APP_DIRS['config_dir'], config_name),
            os.path.join(APP_DIRS['default_config_dir'], config_name)
        ]
    else:
        # In development mode, we only use the repo's config directory
        return [os.path.join(APP_DIRS['config_dir'], config_name)]

def ensure_default_configs():
    """
    Ensure default configs exist in user config directory.
    
    For a packaged app, this copies any missing configs from
    the bundled default configs to the user's config directory.
    """
    if not IS_FROZEN:
        # In development, we don't need to copy configs
        return
    
    # Make sure config directory exists
    os.makedirs(APP_DIRS['config_dir'], exist_ok=True)
    
    # Copy default configs if they exist
    default_dir = APP_DIRS['default_config_dir']
    if os.path.exists(default_dir):
        for filename in os.listdir(default_dir):
            src = os.path.join(default_dir, filename)
            dst = os.path.join(APP_DIRS['config_dir'], filename)
            
            # Only copy if source is a file and destination doesn't exist
            if os.path.isfile(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    logger.info(f"Copied default config: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to copy default config {filename}: {str(e)}") 