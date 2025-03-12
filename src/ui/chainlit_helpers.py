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
from src.global_config import AUTH_TOKEN_FILE

def handle_authentication():
    """
    Handle authentication for the Chainlit app.
    
    Returns:
        tuple: (auth_token, user_info, session_data)
    """
    auth_token = None
    user_info = {"id": None, "name": "Anonymous", "email": "anonymous@example.com"}
    session_data = None
    
    # Try reading from the auth token file first - our reliable IPC method
    try:
        if os.path.exists(AUTH_TOKEN_FILE):
            with open(AUTH_TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
                auth_token = token_data.get("token")
                token_timestamp = token_data.get("timestamp", 0)
                token_age = int(time.time()) - token_timestamp
                
                # Check if token is not too old (max 24 hours)
                if token_age < 24 * 60 * 60:
                    logger.info(f"Found auth_token in {AUTH_TOKEN_FILE}. Token age: {token_age} seconds")
                else:
                    logger.warning(f"Auth token in file is too old ({token_age} seconds). Ignoring.")
                    auth_token = None
    except Exception as e:
        logger.error(f"Error reading auth token from file: {str(e)}")
        
    # If token file approach failed, try the URL parameter methods
    if not auth_token:
        # Method 1: Try to get URL parameters directly from the URL query in user session
        url_query = cl.user_session.get("url_query")
        if url_query and isinstance(url_query, dict) and "auth_token" in url_query:
            auth_token = url_query.get("auth_token")
            logger.info(f"Found auth_token in cl.user_session.url_query: Length {len(auth_token) if auth_token else 0}")
        
        # Method 2: Try to get the token from environment variables
        elif os.getenv("CL_URL_PARAMS"):
            try:
                url_params = json.loads(os.getenv("CL_URL_PARAMS", "{}"))
                auth_token = url_params.get("auth_token")
                logger.info(f"Found auth_token in CL_URL_PARAMS: Length {len(auth_token) if auth_token else 0}")
            except Exception as e:
                logger.error(f"Error parsing CL_URL_PARAMS: {str(e)}")
        
        # Method 3: Try getting from custom environment variable set by auth.py
        elif os.getenv("CHAINLIT_AUTH_TOKEN"):
            auth_token = os.getenv("CHAINLIT_AUTH_TOKEN")
            logger.info(f"Found auth_token in CHAINLIT_AUTH_TOKEN env var: Length {len(auth_token) if auth_token else 0}")
    
    if auth_token:
        try:
            # Decode the token - improved error handling
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
                
                # Log available tokens for debugging
                token_types = []
                if 'google_id_token' in session_data:
                    token_types.append("Google ID Token")
                if 'google_access_token' in session_data:
                    token_types.append("Google Access Token")
                if 'id_token' in session_data:
                    token_types.append("Cognito ID Token")
                if 'access_token' in session_data:
                    token_types.append("Cognito Access Token")
                
                if token_types:
                    logger.info(f"Available auth tokens: {', '.join(token_types)}")
                else:
                    logger.warning("No authentication tokens found in session data")
                    
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
        logger.warning("No auth token found in URL parameters")
        
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
        
    logger.info(f"Using authentication for user: {session_data.get('email', 'unknown')}")
    
    # Log which tokens we have
    auth_tokens = []
    if 'google_id_token' in session_data and session_data['google_id_token']:
        auth_tokens.append("Google ID Token")
    if 'google_access_token' in session_data and session_data['google_access_token']:
        auth_tokens.append("Google Access Token") 
    if 'id_token' in session_data and session_data['id_token']:
        auth_tokens.append("Cognito ID Token")
    if 'access_token' in session_data and session_data['access_token']:
        auth_tokens.append("Cognito Access Token")
    
    if auth_tokens:
        logger.info(f"Available auth tokens: {', '.join(auth_tokens)}")
    else:
        logger.warning("Session data exists but contains no valid authentication tokens")