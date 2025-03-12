import chainlit as cl
import sys
import os
import logging
import traceback
import re

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import log_manager first to ensure proper logging configuration 
from src.logger.log_manager import log_manager

# Import global configuration
from src.global_config import STATE_FILE_PATH

# Force reconfigure logging for the Chainlit process
log_manager.reconfigure()

# Import needed modules
from src.gsi.state_manager import state_manager
from src.ui.history_manager import save_chat_history
from src.cloud.api import configure_process_query_api, call_process_query_api
from src.ui.chainlit_helpers import (
    handle_authentication,
    log_authentication_status
)

# Configure module logger - use getLogger instead of basicConfig
logger = logging.getLogger(__name__)

# Log the loaded configuration
logger.info("Using global configuration from global_config.py")

# Get the API URL
PROCESS_QUERY_API_URL = configure_process_query_api()

# Define starter suggestions for the landing page
@cl.set_starters
async def set_starters():
    """Set the starter messages for the landing page."""
    return [
        cl.Starter(
            label="Hero Performance Analysis",
            message="What are some advanced tips to improve my gameplay with my current hero?",
        ),
        cl.Starter(
            label="Optimal Itemization Guide",
            message="Suggest the best item build based on my current game state and enemy lineup.",
        ),
        cl.Starter(
            label="Team Fight Tactics",
            message="What's the best approach for upcoming team fights based on our lineup?",
        )
    ]

@cl.on_chat_start
async def start():
    """Initialize the chat session without sending any welcome message."""
    try:
        # Handle authentication before showing starters
        auth_token, user_info, session_data = handle_authentication()
        
        # Store authentication information in user session for later use
        cl.user_session.set("auth_token", auth_token)
        cl.user_session.set("user_info", user_info)
        cl.user_session.set("session_data", session_data)
        
        # We don't need to do anything else - the starters will be shown automatically
        # thanks to the @cl.set_starters decorator above
        logger.info("Chat session initialized")
        
    except Exception as e:
        logger.error(f"Error in on_chat_start: {str(e)}")
        logger.error(traceback.format_exc())

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
                logger.debug(f"Found potential query params container: {name}")
                
        return {}
    except Exception as e:
        logger.error(f"Error extracting URL params directly: {str(e)}")
        return {}

@cl.on_message
async def on_message(message: cl.Message):
    """Process user messages."""
    try:
        # Get user info from user session
        user_info = cl.user_session.get("user_info", {
            "id": None,
            "name": "Anonymous",
            "email": "anonymous@example.com"
        })
        
        logger.info(f"Received query from {user_info.get('name', 'Anonymous')}: {message.content[:50]}...")
        
        # Get session data from user_session
        session_data = cl.user_session.get("session_data")
        
        # Remove session recovery logic
        # Let authentication flow handle expired sessions naturally
        
        # Log authentication status
        log_authentication_status(session_data)
        
        # Get game state
        game_state = state_manager.get_state()
        logger.debug(f"Game state: {game_state}")
        
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
                logger.error(f"API error: {error_msg}")
                
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
            logger.info(f"Received answer: {answer[:50]}...")
            
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
            
            # Save the chat history to the session directory
            if user_info and user_info.get("id"):
                try:
                    user_id = user_info.get("id")
                    # Save the chat history using the history_manager
                    save_chat_history(
                        user_id=user_id,
                        query=message.content,
                        response=clean_answer,
                        thinking_content=thinking_content
                    )
                    logger.info(f"Saved chat history for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving chat history: {str(e)}")
            else:
                logger.warning("No user ID available for saving chat history")
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            logger.error(traceback.format_exc())
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


# When this file is run directly by Chainlit CLI (via subprocess from auth.py),
# this code will execute
if __name__ == "__main__":
    logger.info("Chainlit app module loaded directly by Chainlit CLI")
    logger.info(f"Using API URL: {PROCESS_QUERY_API_URL}")
    logger.info(f"Using state file: {STATE_FILE_PATH}")