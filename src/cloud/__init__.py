"""
Cloud module for handling cloud service configurations and interactions.
This module centralizes all cloud-related functionality including API endpoints,
authentication, and service interactions.
""" 

import logging

def setup_api_configuration():
    """Configure API endpoints for cloud services."""
    from src.cloud.api import configure_process_query_api
    from src.config import config
    
    # Pass the pre-configured API URL from config
    api_url = configure_process_query_api(process_query_url=config.process_query_api_url)
    return api_url 