"""
API configuration and management module.
Handles setting up and validating API endpoints for cloud services.
"""
import os
import logging
import json
import aiohttp
import traceback
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
    user_info: Dict[str, Any] = None,
    session_data: Optional[Dict[str, Any]] = None,
    chat_context: Optional[list] = None
) -> Dict[str, Any]:
    """
    Call the process-query API endpoint with the given query and game state.
    
    Args:
        query: The user query
        game_state: The current game state
        user_info: Optional user information
        session_data: Optional session data containing authentication info
        chat_context: Optional chat context in OpenAI format
        
    Returns:
        The API response as a dictionary
    """
    try:
        # Get the API URL from global config
        api_url = configure_process_query_api()
        logger.debug(f"Using API URL: {api_url}")
        
        # Prepare the headers
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Add authentication headers if available
        if session_data:
            # Log email address but not the full session_data
            user_email = session_data.get('email', 'unknown')
            logger.info(f"Preparing API request with auth for user: {user_email}")
            
            # List available Google token types without logging the actual tokens
            token_types = []
            if 'google_id_token' in session_data and session_data['google_id_token']:
                token_types.append('google_id_token')
            if 'google_access_token' in session_data and session_data['google_access_token']:
                token_types.append('google_access_token')
                
            logger.debug(f"Available token types: {token_types}")
            
            # Use token selection with fallback priorities (Google tokens only)
            auth_token = None
            token_source = None
            
            # Priority 1: Google ID token (preferred)
            if 'google_id_token' in session_data and session_data['google_id_token']:
                auth_token = session_data['google_id_token']
                token_source = "google_id_token"
            # Priority 2: Google access token (fallback)
            elif 'google_access_token' in session_data and session_data['google_access_token']:
                auth_token = session_data['google_access_token']
                token_source = "google_access_token"
            
            if auth_token:
                # Validate token format without logging the token content
                if isinstance(auth_token, str) and len(auth_token) > 20:  # basic validation
                    logger.info(f"Using {token_source} for authentication (length: {len(auth_token)})")
                    headers["Authorization"] = f"Bearer {auth_token}"
                    
                    # Add X-Auth-Source header for Google tokens
                    headers["X-Auth-Source"] = "google"
                else:
                    # Log token format issue without exposing token content
                    token_preview = "empty" if not auth_token else (
                        f"{auth_token[:10]}..." if isinstance(auth_token, str) else f"type: {type(auth_token)}"
                    )
                    logger.warning(f"Invalid token format: {token_preview}")
            else:
                logger.warning("No valid Google authentication token found in session data")
        else:
            logger.warning("No session data provided. API call will likely fail with 401 Unauthorized")
        
        # Prepare the request payload
        payload = {
            'query': query,
            'game_state': game_state or {}
        }
        
        # Add user info if available
        if user_info:
            payload['user_info'] = user_info
            
        # Add chat context if available
        if chat_context:
            payload['chat_context'] = chat_context
            logger.debug(f"Including chat context with {len(chat_context)} messages")
        
        logger.info(f"Calling API: {api_url}")
        
        # Log a truncated version of the payload to prevent massive log entries
        payload_str = json.dumps(payload)
        truncated_payload = payload_str[:200] + "..." if len(payload_str) > 200 else payload_str
        logger.debug(f"Request payload (truncated): {truncated_payload}")
        
        # Create safe headers for logging (reduce duplication)
        safe_headers = headers.copy()
        if 'Authorization' in safe_headers:
            auth_value = safe_headers['Authorization']
            if auth_value.startswith('Bearer '):
                safe_headers['Authorization'] = f"Bearer {auth_value[7:20]}..."
        logger.debug(f"Request headers: {safe_headers}")
        
        # Define timeout to prevent hanging
        timeout = aiohttp.ClientTimeout(total=30, connect=30, sock_connect=30, sock_read=30)
        
        # Make the API call using aiohttp (asynchronous)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info("API call successful")
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"API call failed with status {response.status}: {error_text[:500]}")
                        
                        # More detailed error for 401
                        if response.status == 401:
                            return {
                                "error": f"API call failed with status 401 (Unauthorized)",
                                "response": "I encountered an authentication error. This will be fixed when the Lambda functions are updated with the latest code that supports Google authentication."
                            }
                        
                        return {
                            "error": f"API call failed with status {response.status}",
                            "response": "I encountered an error while processing your request."
                        }
            except aiohttp.ClientError as e:
                logger.error(f"Network error during API call: {str(e)}")
                return {
                    "error": f"Network error: {str(e)}",
                    "response": "I encountered a network issue while processing your request. Please try again."
                }
    except Exception as e:
        logger.error(f"Exception during API call: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            "error": f"Exception during API call: {str(e)}",
            "response": "I encountered an error while processing your request."
        } 