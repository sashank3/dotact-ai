"""
API configuration and management module.
Handles setting up and validating API endpoints for cloud services.
"""
import os
import logging
import json
import requests
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def configure_process_query_api() -> str:
    """
    Configure the API endpoint for processing queries.
    
    Returns:
        str: The configured API endpoint URL
    """
    # Get API base URL from environment
    api_base_url = os.getenv("API_BASE_URL")
    process_query_api_url = os.getenv("PROCESS_QUERY_API_URL")
    
    # If PROCESS_QUERY_API_URL is not set but API_BASE_URL is available, construct it
    if not process_query_api_url and api_base_url:
        process_query_api_url = f"{api_base_url}/process-query"
        logger.info(f"Constructed process query API URL: {process_query_api_url}")
    
    if not process_query_api_url:
        logger.warning("No API URL configured for process-query. API calls will fail.")
    else:
        logger.info(f"Using process query API URL: {process_query_api_url}")
    
    return process_query_api_url

async def call_process_query_api(
    query: str, 
    game_state: Dict[str, Any], 
    user_info: Dict[str, Any],
    session_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call the process-query API endpoint.
    
    Args:
        query: The user's query text
        game_state: The current game state
        user_info: Information about the user
        session_data: Optional session data containing auth tokens
        
    Returns:
        Dict[str, Any]: The API response
    """
    api_url = os.getenv("PROCESS_QUERY_API_URL")
    
    if not api_url:
        logger.error("Process query API URL not configured")
        return {"error": "API not configured", "response": "I'm unable to process your request at the moment."}
    
    # Prepare headers with authentication if available
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add authentication token if available in session data
    if session_data:
        logger.info(f"Preparing API request with auth for user: {session_data.get('email')}")
        
        # List available token types in session_data
        token_types = []
        if 'id_token' in session_data and session_data['id_token']:
            token_types.append('id_token')
        if 'access_token' in session_data and session_data['access_token']:
            token_types.append('access_token')
        if 'google_id_token' in session_data and session_data['google_id_token']:
            token_types.append('google_id_token')
        if 'google_access_token' in session_data and session_data['google_access_token']:
            token_types.append('google_access_token')
            
        logger.debug(f"Available token types: {token_types}")
        
        # Use token selection with fallback priorities
        auth_token = None
        token_source = None
        
        # Priority 1: Cognito ID token (most secure)
        if 'id_token' in session_data and session_data['id_token']:
            auth_token = session_data['id_token']
            token_source = "cognito_id_token"
        # Priority 2: Google ID token
        elif 'google_id_token' in session_data and session_data['google_id_token']:
            auth_token = session_data['google_id_token']
            token_source = "google_id_token"
        # Priority 3: Cognito access token
        elif 'access_token' in session_data and session_data['access_token']:
            auth_token = session_data['access_token']
            token_source = "cognito_access_token"
        # Priority 4: Google access token
        elif 'google_access_token' in session_data and session_data['google_access_token']:
            auth_token = session_data['google_access_token']
            token_source = "google_access_token"
        
        if auth_token:
            # Validate token format
            if isinstance(auth_token, str) and len(auth_token) > 20:  # basic validation
                logger.info(f"Using {token_source} for authentication (length: {len(auth_token)})")
                headers["Authorization"] = f"Bearer {auth_token}"
                
                # Add X-Auth-Source header for Google tokens
                if token_source and token_source.startswith("google_"):
                    headers["X-Auth-Source"] = "google"
                    logger.debug(f"Token (first 20 chars): {auth_token[:20]}...")
            else:
                logger.warning(f"Invalid token format or empty token: {auth_token[:10] if isinstance(auth_token, str) else type(auth_token)}")
        else:
            logger.warning("No valid authentication token found in session data")
    else:
        logger.warning("No session data provided. API call will likely fail with 401 Unauthorized")
    
    # Prepare payload
    payload = {
        "query": query,
        "game_state": game_state,
        "user_info": user_info
    }
    
    logger.info(f"Calling API: {api_url}")
    logger.debug(f"Request payload: {json.dumps(payload)[:200]}...")
    
    try:
        # Log headers (without the full token for security)
        safe_headers = headers.copy()
        if 'Authorization' in safe_headers:
            auth_value = safe_headers['Authorization']
            if auth_value.startswith('Bearer '):
                safe_headers['Authorization'] = f"Bearer {auth_value[7:20]}..."
        logger.debug(f"Request headers: {safe_headers}")
        
        # Make the API call
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info("API call successful")
            return response.json()
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            
            # More detailed error for 401
            if response.status_code == 401:
                return {
                    "error": f"API call failed with status 401 (Unauthorized)",
                    "response": "I encountered an authentication error. This will be fixed when the Lambda functions are updated with the latest code that supports Google authentication."
                }
            
            return {
                "error": f"API call failed with status {response.status_code}",
                "response": "I encountered an error while processing your request."
            }
    except Exception as e:
        logger.error(f"Exception during API call: {str(e)}")
        return {
            "error": f"Exception during API call: {str(e)}",
            "response": "I encountered an error while processing your request."
        } 