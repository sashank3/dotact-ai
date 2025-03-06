import chainlit as cl
import sys
import os
import logging
import traceback
import base64
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
import time
import json
import re

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import STATE_FILE_PATH, AUTH_TOKEN_FILE

# Force reconfigure logging for the Chainlit process
from src.logger.log_manager import log_manager
log_manager.reconfigure()  # Add this line

# Updated import path for state_manager
from src.gsi.state_manager import state_manager
from src.ui.history_manager import save_chat_history, load_chat_history, clear_chat_history
from src.cloud.api import configure_process_query_api, call_process_query_api

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log the loaded configuration
logger.info("Using global configuration from global_config.py")

# Get the API URL
PROCESS_QUERY_API_URL = configure_process_query_api()

# Create serializer for secure cookie data (must match auth.py)
SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY", "default-secret-key")
serializer = URLSafeSerializer(SECRET_KEY)

# Session storage for authenticated users
user_sessions = {}

# Helper function to try to extract URL parameters directly
def get_url_query_params():
    """
    Attempt to extract URL query parameters directly from the Chainlit context.
    This uses a more direct approach to access query parameters.
    
    Returns:
        dict: URL query parameters or empty dict if not found
    """
    try:
        # Try to get access to the fastapi request object via the Chainlit context
        import inspect
        from chainlit.context import get_context
        
        ctx = get_context()
        if ctx and hasattr(ctx, 'request'):
            request = ctx.request
            if hasattr(request, 'query_params'):
                # Convert query_params to dict
                return {k: v for k, v in request.query_params.items()}
        
        # Fallback: try to access via globals or other means
        import sys
        for name, obj in inspect.getmembers(sys.modules['chainlit']):
            if hasattr(obj, 'query_params') or hasattr(obj, 'request'):
                logging.debug(f"Found potential query params container: {name}")
                
        return {}
    except Exception as e:
        logging.error(f"Error extracting URL params directly: {str(e)}")
        return {}

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    try:
        # Check for auth token in token file (primary method)
        auth_token = None
        
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
                        logging.info(f"Found auth_token in {AUTH_TOKEN_FILE}. Token age: {token_age} seconds")
                    else:
                        logging.warning(f"Auth token in file is too old ({token_age} seconds). Ignoring.")
                        auth_token = None
        except Exception as e:
            logging.error(f"Error reading auth token from file: {str(e)}")
            
        # If token file approach failed, try the URL parameter methods
        if not auth_token:
            # Method 1: Try to get URL parameters directly from the URL query in user session
            url_query = cl.user_session.get("url_query")
            if url_query and isinstance(url_query, dict) and "auth_token" in url_query:
                auth_token = url_query.get("auth_token")
                logging.info(f"Found auth_token in cl.user_session.url_query: Length {len(auth_token) if auth_token else 0}")
            
            # Method 2: Try to get the token from environment variables
            elif os.getenv("CL_URL_PARAMS"):
                try:
                    url_params = json.loads(os.getenv("CL_URL_PARAMS", "{}"))
                    auth_token = url_params.get("auth_token")
                    logging.info(f"Found auth_token in CL_URL_PARAMS: Length {len(auth_token) if auth_token else 0}")
                except Exception as e:
                    logging.error(f"Error parsing CL_URL_PARAMS: {str(e)}")
            
            # Method 3: Try getting from custom environment variable set by auth.py
            elif os.getenv("CHAINLIT_AUTH_TOKEN"):
                auth_token = os.getenv("CHAINLIT_AUTH_TOKEN")
                logging.info(f"Found auth_token in CHAINLIT_AUTH_TOKEN env var: Length {len(auth_token) if auth_token else 0}")
        
        user_info = {"id": None, "name": "Anonymous", "email": "anonymous@example.com"}
        session_data = None
        
        if auth_token:
            try:
                # Decode the token - improved error handling
                logging.info(f"Auth token found. Length: {len(auth_token)}")
                try:
                    # First try standard base64 decoding
                    decoded_token = base64.urlsafe_b64decode(auth_token.encode()).decode()
                    logging.debug(f"Successfully decoded auth token (first 20 chars): {decoded_token[:20]}")
                except Exception as e:
                    logging.error(f"Error decoding base64 token: {str(e)}")
                    logging.debug(f"Raw token: {auth_token[:30]}...")
                    # Try without base64 decoding as fallback
                    decoded_token = auth_token
                
                # Store the session token for this user
                user_session_id = cl.user_session.get("id")
                if user_session_id:
                    user_sessions[user_session_id] = decoded_token
                    logging.info(f"Stored session token for user session ID: {user_session_id}")
                else:
                    logging.warning("No user session ID available to store token")
                
                # Extract user info from token if possible
                try:
                    # Load session data from token
                    session_data = serializer.loads(decoded_token)
                    logging.info(f"Loaded session data for {session_data.get('email')}")
                    
                    # Extract user info
                    user_info = {
                        "id": session_data.get("user_id"),
                        "name": session_data.get("name", "User"),
                        "email": session_data.get("email", "user@example.com")
                    }
                    logging.info(f"Authenticated user: {user_info['name']} ({user_info['email']})")
                    
                    # Store session_data in user_session for later use in API calls
                    cl.user_session.set("session_data", session_data)
                    cl.user_session.set("user_info", user_info)
                    
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
                        logging.info(f"Available auth tokens: {', '.join(token_types)}")
                    else:
                        logging.warning("No authentication tokens found in session data")
                        
                except BadSignature:
                    logging.error("Invalid token signature")
                except SignatureExpired:
                    logging.error("Token has expired")
                except Exception as e:
                    logging.error(f"Error parsing session data: {str(e)}")
                    logging.debug(f"Session data content type: {type(decoded_token)}")
                    if isinstance(decoded_token, str):
                        logging.debug(f"Session data content (first 50 chars): {decoded_token[:50]}...")
            except Exception as e:
                logging.error(f"Error processing auth token: {str(e)}")
        else:
            logging.warning("No auth token found in URL parameters")
        
        # Try to load chat history if we have a user ID
        if user_info and user_info.get("id"):
            try:
                user_id = user_info.get("id")
                history = load_chat_history(user_id)
                if history:
                    logging.info(f"Loaded {len(history)} chat messages from history for user {user_id}")
                    for msg in history:
                        if msg.get("role") == "user":
                            await cl.Message(content=msg.get("content"), author=user_info.get("name")).send()
                        else:
                            await cl.Message(content=msg.get("content"), author="Assistant").send()
            except Exception as e:
                logging.error(f"Error loading chat history: {str(e)}")
        else:
            logging.warning("No user ID available for loading chat history")
        
        # Send personalized welcome message
        if user_info and user_info.get("name") != "Anonymous":
            await cl.Message(
                content=f"Welcome back, {user_info.get('name')}! I'm your Dota 2 assistant. How can I help you today?",
                author="Keenmind"
            ).send()
        else:
            await cl.Message(
                content=f"Welcome to Keenmind! I'm your Dota 2 assistant. How can I help you today?",
                author="Keenmind"
            ).send()
        
    except Exception as e:
        logger.error(f"Error in on_chat_start: {str(e)}")
        logger.error(traceback.format_exc())
        await cl.Message(
            content="Sorry, there was an error initializing the chat. Please try refreshing the page.",
            author="System"
        ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Process user messages."""
    try:
        user_info = cl.user_session.get("user_info", {
            "id": None,
            "name": "Anonymous",
            "email": "anonymous@example.com"
        })
        
        logging.info(f"Received query from {user_info.get('name', 'Anonymous')}: {message.content[:50]}...")
        
        # Get session data from user_session
        session_data = cl.user_session.get("session_data")
        
        # If not in user_session, try to recover from stored token
        if not session_data:
            user_session_id = cl.user_session.get("id")
            session_token = user_sessions.get(user_session_id)
            
            if session_token:
                try:
                    session_data = serializer.loads(session_token)
                    logging.info(f"Recovered session data for {session_data.get('email')} from stored token")
                    # Store it in the session for future use
                    cl.user_session.set("session_data", session_data)
                except Exception as e:
                    logging.error(f"Error loading session data from stored token: {str(e)}")
        
        # Log authentication status
        if session_data:
            logging.info(f"Using authentication for user: {session_data.get('email')}")
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
                logging.info(f"Available auth tokens: {', '.join(auth_tokens)}")
            else:
                logging.warning("Session data exists but contains no valid authentication tokens")
        else:
            logging.warning("No session data available. API calls will not be authenticated.")
        
        # Get game state
        game_state = state_manager.get_state()
        logging.debug(f"Game state: {game_state}")
        
        # Process query using API
        try:
            response = await call_process_query_api(
                query=message.content,
                game_state=game_state,
                user_info=user_info,
                session_data=session_data
            )
            
            # Check for errors
            if "error" in response:
                error_msg = response.get('error', 'Unknown error')
                logging.error(f"API error: {error_msg}")
                
                # Provide a helpful message for authentication errors
                if '401' in error_msg or 'Unauthorized' in error_msg:
                    await cl.Message(
                        content="I'm having trouble authenticating your request. This might be due to an expired session or missing authentication tokens. You may need to log out and log back in.",
                        author="System"
                    ).send()
                else:
                    await cl.Message(
                        content=f"Sorry, there was an error processing your query: {error_msg}",
                        author="System"
                    ).send()
                return
            
            # Get the response text
            answer = response.get("answer", "Sorry, I couldn't find an answer to your query.")
            logging.info(f"Received answer: {answer[:50]}...")
            
            # Extract content between <think> and </think> tags
            thinking_pattern = r'<think>(.*?)</think>'
            thinking_matches = re.findall(thinking_pattern, answer, re.DOTALL)
            
            # Join all thinking content if multiple matches
            thinking_content = "\n".join(thinking_matches) if thinking_matches else ""
            
            # Remove all <think>...</think> blocks from the answer
            clean_answer = re.sub(thinking_pattern, '', answer, flags=re.DOTALL)
            
            # If we have thinking content, display it in a Step
            if thinking_content:
                async with cl.Step(name="Thinking") as thinking_step:
                    await thinking_step.stream_token(thinking_content)
                    thinking_step.name = "Keenmind's Reasoning"
                    await thinking_step.update()
            
            # Send the clean response
            await cl.Message(content=clean_answer).send()
            
            # # Save chat history if we have a user ID
            # if user_info and user_info.get("id"):
            #     save_chat_history(
            #         user_id=user_info.get("id"),
            #         query=message.content,
            #         response=answer,
            #         metadata={
            #             "game_state_summary": response.get("game_state_summary", {}),
            #             "timestamp": response.get("timestamp")
            #         }
            #     )
            # else:
            #     logging.warning("No user ID available for saving chat history")
            
        except Exception as e:
            logging.error(f"Error processing query: {str(e)}")
            logging.error(traceback.format_exc())
            await cl.Message(
                content="Sorry, there was an error processing your query. Please try again.",
                author="System"
            ).send()
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        await cl.Message(
            content="Sorry, there was an error processing your query. Please try again.",
            author="System"
        ).send()

# @cl.action_callback("clear_history")
# async def clear_history_action(action):
#     """Clear chat history for the current user."""
#     try:
#         user_id = cl.user_session.get("user_id")
#         if not user_id:
#             await cl.Message(content="No user ID found. Cannot clear history.").send()
#             return
            
#         clear_chat_history(user_id)
#         await cl.Message(content="Chat history cleared successfully!").send()
        
#     except Exception as e:
#         logger.error(f"Error clearing history: {str(e)}")
#         await cl.Message(content=f"Error clearing history: {str(e)}").send()

# Note: This module doesn't need a run_chainlit() function because:
# 1. It's loaded directly by the Chainlit CLI when started by auth.py
# 2. The auth.py module handles starting the Chainlit process with the correct parameters

# When this file is run directly by Chainlit CLI (via subprocess from auth.py),
# this code will execute
if __name__ == "__main__":
    logger.info("Chainlit app module loaded directly by Chainlit CLI")
    logger.info(f"Using API URL: {PROCESS_QUERY_API_URL}")
    logger.info(f"Using state file: {STATE_FILE_PATH}")