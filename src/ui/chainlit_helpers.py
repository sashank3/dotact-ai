import os
import json
import logging
import base64
import time
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
import chainlit as cl

# Configure logging
logger = logging.getLogger(__name__)

# Create serializer for secure cookie data (must match auth.py)
SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY", "default-secret-key")
serializer = URLSafeSerializer(SECRET_KEY)

# Import from global config
from src.global_config import AUTH_TOKEN_FILE, AUTH_SESSION_MAX_AGE

def handle_authentication():
    """
    Handle authentication for the Chainlit app.
    
    Returns:
        tuple: (auth_token, user_info, session_data)
    """
    auth_token = None
    user_info = {"id": None, "name": "Anonymous", "email": "anonymous@example.com"}
    session_data = None
    
    # Read from the auth token file - our reliable method
    try:
        if os.path.exists(AUTH_TOKEN_FILE):
            with open(AUTH_TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
                auth_token = token_data.get("token")
                token_timestamp = token_data.get("timestamp", 0)
                token_age = int(time.time()) - token_timestamp
                
                # Check if token is not too old (max 48 hours)
                if token_age < AUTH_SESSION_MAX_AGE:
                    logger.info(f"Found auth_token in {AUTH_TOKEN_FILE}. Token age: {token_age} seconds")
                else:
                    logger.warning(f"Auth token in file is too old ({token_age} seconds). Ignoring.")
                    auth_token = None
    except Exception as e:
        logger.error(f"Error reading auth token from file: {str(e)}")
    
    if auth_token:
        try:
            # Decode the token
            logger.info(f"Auth token found. Length: {len(auth_token)}")
            try:
                # First try standard base64 decoding
                decoded_token = base64.urlsafe_b64decode(auth_token.encode()).decode()
                logger.debug(f"Successfully decoded auth token (first 20 chars): {decoded_token[:20]}")
            except Exception as e:
                logger.error(f"Error decoding base64 token: {str(e)}")
                logger.debug(f"Raw token: {auth_token[:30]}...")
                # Try without base64 decoding as fallback
                decoded_token = auth_token
            
            # Extract user info from token if possible
            try:
                # Load session data from token
                session_data = serializer.loads(decoded_token)
                logger.info(f"Loaded session data for {session_data.get('email')}")
                
                # Extract user info
                user_info = {
                    "id": session_data.get("user_id"),
                    "name": session_data.get("name", "User"),
                    "email": session_data.get("email", "user@example.com")
                }
                logger.info(f"Authenticated user: {user_info['name']} ({user_info['email']})")
                
                # Log available Google tokens for debugging
                token_types = []
                if 'google_id_token' in session_data:
                    token_types.append("Google ID Token")
                if 'google_access_token' in session_data:
                    token_types.append("Google Access Token")
                
                if token_types:
                    logger.info(f"Available auth tokens: {', '.join(token_types)}")
                else:
                    logger.warning("No Google authentication tokens found in session data")
                    
            except BadSignature:
                logger.error("Invalid token signature")
            except SignatureExpired:
                logger.error("Token has expired")
            except Exception as e:
                logger.error(f"Error parsing session data: {str(e)}")
                logger.debug(f"Session data content type: {type(decoded_token)}")
                if isinstance(decoded_token, str):
                    logger.debug(f"Session data content (first 50 chars): {decoded_token[:50]}...")
        except Exception as e:
            logger.error(f"Error processing auth token: {str(e)}")
    else:
        logger.warning("No auth token found in token file")
        
    return auth_token, user_info, session_data

def recover_session_data(user_session_id):
    """
    Minimal stub for recover_session_data. 
    
    As per user's requirements, this simply returns None, enforcing re-login
    when a session expires.
    
    Returns:
        None: Always returns None to enforce re-authentication
    """
    # Per user's request, this function should not actually recover sessions
    logger.info("Session recovery disabled per user request. Users must re-authenticate.")
    return None

def log_authentication_status(session_data):
    """
    Log the current authentication status based on session data.
    
    Args:
        session_data (dict): The session data containing authentication tokens
    """
    if not session_data:
        logger.warning("No session data available. API calls will not be authenticated.")
        return
        
    if not isinstance(session_data, dict):
        logger.error(f"Invalid session data type: {type(session_data)}")
        return
    
    # Log basic auth info
    logger.info(f"Using authentication for user: {session_data.get('email', 'unknown')}")
    
    # Check for Google tokens only
    has_google_id = 'google_id_token' in session_data and session_data['google_id_token']
    has_google_access = 'google_access_token' in session_data and session_data['google_access_token']
    
    if has_google_id or has_google_access:
        token_types = []
        if has_google_id:
            token_types.append("Google ID Token")
        if has_google_access:
            token_types.append("Google Access Token")
        logger.info(f"Available auth tokens: {', '.join(token_types)}")
    else:
        logger.warning("Session data exists but contains no valid Google authentication tokens")

def process_conversation_history(conversation_history, max_interactions=5):
    """
    Process the conversation history to ensure it's properly formatted.
    
    Args:
        conversation_history: List of messages in OpenAI format
        max_interactions: Maximum number of query/response pairs to include
        
    Returns:
        List of processed messages
    """
    if not conversation_history:
        return []
    
    # Ensure we only have user and assistant messages (no system messages)
    filtered_history = [
        msg for msg in conversation_history 
        if msg.get("role") in ["user", "assistant"]
    ]
    
    # Limit to the latest messages (max_interactions * 2 since each interaction is a pair)
    max_messages = max_interactions * 2
    if len(filtered_history) > max_messages:
        filtered_history = filtered_history[-max_messages:]
    
    return filtered_history