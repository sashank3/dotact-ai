import os
import sys
from src.bootstrap import is_frozen, get_application_root
import logging
import yaml

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
    In prod: C:/Users/[Username]/AppData/Roaming/Keenplay/data
    """
    if is_frozen():
        # In production, use AppData/Roaming for user data
        app_data = os.path.join(os.environ['APPDATA'], 'Keenplay', 'data')
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
    In prod: C:/Users/[Username]/AppData/Local/Keenplay/logs
    """
    if is_frozen():
        # In production, use AppData/Local for logs
        local_app_data = os.path.join(os.environ['LOCALAPPDATA'], 'Keenplay', 'logs')
        os.makedirs(local_app_data, exist_ok=True)
        return local_app_data
    else:
        # In development, use repo/logs
        logs_path = os.path.join(get_application_root(), 'logs')
        os.makedirs(logs_path, exist_ok=True)
        return logs_path

def read_steam_path_config(config_path):
    """
    Safely reads the steam_path.yaml file, handling Windows path backslashes correctly.
    Returns a dictionary with the Steam configuration.
    """
    if not config_path or not os.path.exists(config_path):
        return None
        
    try:
        # First try raw reading the file to handle it directly
        with open(config_path, 'r') as file:
            content = file.read()
            
        # Create a basic structure that matches expected format
        config = {'steam': {}}
        
        # Direct pattern matching for the specific fields we need
        path_match = content.find('path:')
        gsi_path_match = content.find('gsi_path:')
        
        # Extract the path values
        if path_match != -1:
            path_line = content[path_match:].split('\n')[0]
            path_value = path_line.split(':', 1)[1].strip()
            if path_value.startswith('"') and path_value.endswith('"'):
                path_value = path_value[1:-1]
            config['steam']['path'] = path_value
            
        if gsi_path_match != -1:
            gsi_line = content[gsi_path_match:].split('\n')[0]
            gsi_value = gsi_line.split(':', 1)[1].strip()
            if gsi_value.startswith('"') and gsi_value.endswith('"'):
                gsi_value = gsi_value[1:-1]
            config['steam']['gsi_path'] = gsi_value
            
        # Add first_install flag if it exists in the file
        if 'first_install:' in content:
            first_install_line = content[content.find('first_install:'):].split('\n')[0]
            first_install_value = first_install_line.split(':', 1)[1].strip().lower()
            config['steam']['first_install'] = first_install_value == 'true'
            
        # Validate that we have the minimum required fields
        if not config['steam'].get('path') or not config['steam'].get('gsi_path'):
            logging.warning("Missing required fields in steam configuration")
            
        return config
            
    except Exception as e:
        logging.error(f"Failed to parse steam configuration file: {e}")
        return None 