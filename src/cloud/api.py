"""
API configuration and management module.
Handles setting up and validating API endpoints for cloud services.
"""
import os
import logging
import json
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
    Call the process-query API with the user's query and game state.
    
    Args:
        query (str): The user's query
        game_state (Dict[str, Any]): The current game state
        user_info (Dict[str, Any]): Information about the user
        session_data (Optional[Dict[str, Any]]): Session data including auth tokens
        
    Returns:
        Dict[str, Any]: The API response
    """
    import aiohttp
    
    # Get API URL
    api_url = os.getenv("PROCESS_QUERY_API_URL")
    if not api_url:
        api_url = configure_process_query_api()
        
    if not api_url:
        error_msg = "No API URL configured for process-query. Cannot make API call."
        logger.error(error_msg)
        return {"error": error_msg}
    
    # Prepare headers with authentication if available
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add Cognito token if available in session data
    if session_data and session_data.get("cognito_token"):
        headers["Authorization"] = f"Bearer {session_data['cognito_token']}"
        logger.debug("Using Cognito token for API authorization")
    
    # Prepare request payload
    payload = {
        "query": query,
        "game_state": game_state,
        "user_info": user_info
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Calling API: {api_url}")
            logger.debug(f"Request payload: {json.dumps(payload)[:500]}...")
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API call failed with status {response.status}: {error_text}")
                    return {
                        "error": f"API call failed with status {response.status}",
                        "details": error_text
                    }
                
                result = await response.json()
                logger.info("API call successful")
                logger.debug(f"API response: {json.dumps(result)[:500]}...")
                return result
                
    except Exception as e:
        error_msg = f"Error calling API: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg} 