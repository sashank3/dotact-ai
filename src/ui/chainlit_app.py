import chainlit as cl
import sys
import os
import logging
import traceback
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import GLOBAL_CONFIG, UI_CONFIG, STATE_FILE_PATH

# Updated import path for state_manager
from src.gsi.state_manager import state_manager
from src.ui.history_manager import save_chat_history, load_chat_history, get_detailed_chat_entry, clear_chat_history
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

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    try:
        # Get user info
        user_id = cl.user_session.get("user_id")
        user_info = {
            "id": user_id,
            "name": cl.user_session.get("name", "Anonymous"),
            "email": cl.user_session.get("email", "anonymous@example.com")
        }
        logger.info(f"Chat started for user: {user_info['name']} ({user_info['email']})")
        
        # Check if user is authenticated
        if not user_info.get("email") or user_info.get("email") == "anonymous@example.com":
            logger.warning("User is not authenticated")
            # We'll continue anyway, but log the warning
        
        # Load chat history
        history = load_chat_history(user_id)
        if history:
            logger.info(f"Loaded {len(history)} chat history entries for user {user_id}")
        
        # Send welcome message
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
    """Handle user messages."""
    try:
        # Get user info
        user_id = cl.user_session.get("user_id")
        user_info = {
            "id": user_id,
            "name": cl.user_session.get("name", "Anonymous"),
            "email": cl.user_session.get("email", "anonymous@example.com")
        }
        
        # Get the query from the message
        query = message.content
        logger.info(f"Received query from {user_info['name']}: {query[:50]}...")
        
        # Check if API URL is configured
        if not PROCESS_QUERY_API_URL:
            logger.error("No API URL configured for process-query")
            await cl.Message(
                content="Sorry, the API endpoint is not configured. Please check your environment variables.",
                author="System"
            ).send()
            return
        
        # Get the current game state
        game_state = state_manager.get_state()
        if not game_state:
            logger.warning("No game state available")
            game_state = {}  # Use empty dict if no state available
        
        # Get session data from cookie if available
        session_data = None
        try:
            # In Chainlit, we need to get the cookie from the request headers
            # This is a simplified approach - in production, you might need to adjust this
            cookies = cl.user_session.get("cookies", {})
            session_cookie = cookies.get("session-data")
            
            if session_cookie:
                session_data = serializer.loads(session_cookie)
                logger.debug(f"Found session data for {session_data.get('email')}")
            else:
                logger.debug("No session cookie found")
        except (BadSignature, SignatureExpired) as e:
            logger.warning(f"Invalid session cookie: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing session cookie: {str(e)}")
        
        # Show thinking indicator
        await cl.Message(content="Thinking...").send()
        
        # Call the API
        response = await call_process_query_api(
            query=query,
            game_state=game_state,
            user_info=user_info,
            session_data=session_data
        )
        
        # Check for errors
        if "error" in response:
            logger.error(f"API error: {response['error']}")
            await cl.Message(
                content=f"Sorry, there was an error processing your query: {response['error']}",
                author="System"
            ).send()
            return
        
        # Process the response
        answer = response.get("answer", "Sorry, I couldn't find an answer to your query.")
        logger.info(f"Received answer: {answer[:50]}...")
        
        # Send the response
        await cl.Message(content=answer).send()
        
        # Save chat history
        save_chat_history(
            user_id=user_id,
            query=query,
            response=answer,
            metadata={
                "game_state_summary": response.get("game_state_summary", {}),
                "timestamp": response.get("timestamp")
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        await cl.Message(
            content="Sorry, there was an error processing your query. Please try again.",
            author="System"
        ).send()

@cl.action_callback("clear_history")
async def clear_history_action(action):
    """Clear chat history for the current user."""
    try:
        user_id = cl.user_session.get("user_id")
        if not user_id:
            await cl.Message(content="No user ID found. Cannot clear history.").send()
            return
            
        clear_chat_history(user_id)
        await cl.Message(content="Chat history cleared successfully!").send()
        
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        await cl.Message(content=f"Error clearing history: {str(e)}").send()

# Note: This module doesn't need a run_chainlit() function because:
# 1. It's loaded directly by the Chainlit CLI when started by auth.py
# 2. The auth.py module handles starting the Chainlit process with the correct parameters

# When this file is run directly by Chainlit CLI (via subprocess from auth.py),
# this code will execute
if __name__ == "__main__":
    logger.info("Chainlit app module loaded directly by Chainlit CLI")
    logger.info(f"Using API URL: {PROCESS_QUERY_API_URL}")
    logger.info(f"Using state file: {STATE_FILE_PATH}")