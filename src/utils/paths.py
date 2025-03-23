import os
import sys
from src.bootstrap import is_frozen, get_application_root
import logging

def get_config_path():
    """
    Get the path to the config directory
    
    In dev: [repo_root]/config
    In prod: Bundled config from PyInstaller package
    """
    if is_frozen():
        # First priority: Check for configs in the PyInstaller bundle (_MEIPASS)
        if hasattr(sys, '_MEIPASS'):
            bundled_config = os.path.join(sys._MEIPASS, 'config')
            if os.path.exists(bundled_config):
                logging.info(f"Using bundled config from: {bundled_config}")
                return bundled_config
            
        # Fallback: Check for configs in the application directory (unlikely but possible)
        app_config = os.path.join(get_application_root(), 'config')
        if os.path.exists(app_config):
            logging.info(f"Using config from application directory: {app_config}")
            return app_config
            
        # We really shouldn't get here, but just in case, log a warning
        logging.warning("Configuration directory not found in bundled resources!")
        return os.path.join(get_application_root(), 'config')
    else:
        # In development, use repo/config
        config_path = os.path.join(get_application_root(), 'config')
        os.makedirs(config_path, exist_ok=True)
        return config_path

def get_user_data_path():
    """
    Get the path to the user data directory
    
    In dev: [repo_root]/data
    In prod: C:/Users/[Username]/AppData/Roaming/Keenmind/data
    """
    if is_frozen():
        # In production, use AppData/Roaming for user data
        app_data = os.path.join(os.environ['APPDATA'], 'Keenmind', 'data')
        os.makedirs(app_data, exist_ok=True)
        return app_data
    else:
        # In development, use repo/data
        data_path = os.path.join(get_application_root(), 'data')
        os.makedirs(data_path, exist_ok=True)
        return data_path

def get_logs_path():
    """
    Get the path to the logs directory
    
    In dev: [repo_root]/logs
    In prod: C:/Users/[Username]/AppData/Local/Keenmind/logs
    """
    if is_frozen():
        # In production, use AppData/Local for logs
        local_app_data = os.path.join(os.environ['LOCALAPPDATA'], 'Keenmind', 'logs')
        os.makedirs(local_app_data, exist_ok=True)
        return local_app_data
    else:
        # In development, use repo/logs
        logs_path = os.path.join(get_application_root(), 'logs')
        os.makedirs(logs_path, exist_ok=True)
        return logs_path

def get_steam_path_config():
    """
    Returns the path to the steam_path.yaml configuration file.
    
    This file is installed alongside the application executable.
    """
    # First priority: Check application root (where keenmind.exe is)
    app_root = get_application_root()
    steam_config_path = os.path.join(app_root, 'steam_path.yaml')
    
    if os.path.exists(steam_config_path):
        logging.info(f"Using steam path config from application directory: {steam_config_path}")
        return steam_config_path
    
    # In development, check the repo config dir
    if not is_frozen():
        app_config_dir = os.path.join(get_application_root(), 'config')
        steam_config_path = os.path.join(app_config_dir, 'steam_path.yaml')
        if os.path.exists(steam_config_path):
            return steam_config_path
    
    # If not found anywhere, return None
    logging.warning("Steam path configuration not found")
    return None 