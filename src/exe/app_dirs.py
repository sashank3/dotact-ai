import os
import sys
import logging
import shutil

# Configure basic logger
logger = logging.getLogger(__name__)

def get_app_dirs():
    """
    Returns standardized paths that work in both development and executable environments.
    
    Returns a dictionary with paths for:
    - app_root: Root directory of the application
    - data_dir: Directory for user data files
    - config_dir: Directory for configuration files
    - logs_dir: Directory for log files
    - default_config_dir: Directory for default/bundled config files
    """
    # Check if running as PyInstaller executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # We're running as a compiled executable
        exe_dir = os.path.dirname(sys.executable)
        
        # Use Windows AppData folder for user data and settings
        app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Keenmind')
        
        # Use LocalAppData for logs (more appropriate for larger files)
        local_app_data = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', ''))
        logs_dir = os.path.join(local_app_data, 'Keenmind', 'logs')
        
        return {
            'app_root': exe_dir,
            'data_dir': os.path.join(app_data_dir, 'data'),
            'config_dir': os.path.join(app_data_dir, 'config'),
            'logs_dir': logs_dir,
            'default_config_dir': os.path.join(exe_dir, 'config')
        }
    else:
        # We're running in development mode
        app_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".."))
        
        return {
            'app_root': app_root,
            'data_dir': os.path.join(app_root, 'data'),
            'config_dir': os.path.join(app_root, 'config'),
            'logs_dir': os.path.join(app_root, 'logs'),
            'default_config_dir': os.path.join(app_root, 'src', 'default_config')
        }

def ensure_app_dirs():
    """
    Creates all application directories if they don't exist.
    Returns the directory structure dictionary.
    """
    app_dirs = get_app_dirs()
    
    # Create directories if they don't exist
    for dir_path in app_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        
    return app_dirs

def copy_default_configs():
    """
    Copy default configuration files to the user config directory.
    This function only copies files that don't already exist in the user config directory.
    """
    app_dirs = get_app_dirs()
    
    # Skip if we're in development mode
    if not is_frozen():
        return
    
    # Create config directory if it doesn't exist
    os.makedirs(app_dirs['config_dir'], exist_ok=True)
    
    # Check if we have default configs
    default_config_dir = app_dirs['default_config_dir']
    if not os.path.exists(default_config_dir):
        logger.warning(f"Default config directory not found: {default_config_dir}")
        return
    
    # Copy default configs to user config directory if they don't exist
    for filename in os.listdir(default_config_dir):
        src_path = os.path.join(default_config_dir, filename)
        dst_path = os.path.join(app_dirs['config_dir'], filename)
        
        # Only copy if it's a file and it doesn't already exist in user config
        if os.path.isfile(src_path) and not os.path.exists(dst_path):
            try:
                shutil.copy2(src_path, dst_path)
                logger.info(f"Copied default config: {filename}")
            except Exception as e:
                logger.error(f"Failed to copy default config {filename}: {str(e)}")

def is_frozen():
    """
    Returns True if running as a PyInstaller executable,
    False if running in development mode.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Get and ensure app directories at module import time
APP_DIRS = ensure_app_dirs()
IS_FROZEN = is_frozen() 