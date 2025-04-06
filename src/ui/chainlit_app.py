import chainlit as cl
import sys
import os
import logging
import re
import json
import time
# Simple, reliable path handling (Keep this as is)
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, root_dir)

# ==============================================================================
# CRITICAL: Import log_manager *early* to ensure logging is configured
#           for this process using the SESSION_DIR environment variable set by auth.py
# ==============================================================================
print(f"[chainlit_app.py {os.getpid()}] Importing log_manager...", file=sys.stderr)
from src.logger.log_manager import log_manager
print(f"[chainlit_app.py {os.getpid()}] log_manager imported.", file=sys.stderr)
# ==============================================================================

# Import configuration AFTER log_manager might be needed by config itself
from src.config import config

# Import needed modules
from src.gsi.state_manager import state_manager
from src.ui.history_manager import save_chat_history
from src.cloud.api import configure_process_query_api, call_process_query_api
from src.ui.chainlit_helpers import (
    handle_authentication,
    log_authentication_status,
    process_conversation_history
)

# Configure module logger - use getLogger AFTER log_manager is imported/configured
# Use the __name__ convention for specific module logging
logger = logging.getLogger(__name__)

# Initial logs (should now use the correctly configured logger via LogManager)
logger.info("Chainlit application starting up...") # Test log
PROCESS_QUERY_API_URL = configure_process_query_api() # Configures based on environment or config file
logger.info(f"Chainlit App using API URL: {PROCESS_QUERY_API_URL}")


@cl.set_starters
async def set_starters():
    """Set the starter messages for the landing page."""
    logger.debug("Setting starters...") # Use logger
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
    """Initialize the chat session."""
    logger.info("Chainlit on_chat_start executing.") # Logger should work now

    try:
        # Handle authentication before showing starters
        auth_token, user_info, session_data = handle_authentication() # Assumes this function works correctly

        # Store authentication information in user session for later use
        cl.user_session.set("auth_token", auth_token)
        cl.user_session.set("user_info", user_info)
        cl.user_session.set("session_data", session_data)

        logger.info("Chat session initialized and user info stored.")
        if user_info:
             logger.info(f"User: {user_info.get('name', 'Unknown')} ({user_info.get('email', 'No email')})")

    except Exception as e:
        logger.error(f"Error in on_chat_start: {str(e)}", exc_info=True)
        # Optionally inform the user
        await cl.Message(content="An error occurred during chat initialization. Please refresh or try again later.").send()


# Helper function (CORRECTED)
def get_url_query_params():
    """
    Attempt to extract URL query parameters directly from the Chainlit context.
    Uses a safer approach to access potential request object and query parameters.

    Returns:
        dict: URL query parameters or empty dict if not found or error occurs.
    """
    logger.debug("Attempting to extract URL query parameters...")
    try:
        # Import necessary components safely inside the try block
        from chainlit.context import get_context

        ctx = get_context()
        if not ctx:
            logger.debug("Chainlit context (ctx) not found.")
            return {}

        # Safely get the 'request' attribute from the context
        request = getattr(ctx, 'request', None)
        if not request:
            logger.debug("Context found, but 'request' attribute is missing or None.")
            return {}

        # Check if the request object has the 'query_params' attribute
        if not hasattr(request, 'query_params'):
             logger.debug("Context request object found, but has no 'query_params' attribute.")
             return {}

        # Safely get the 'query_params' attribute's value
        query_params = getattr(request, 'query_params', None)
        if query_params is None:
            # This case is less likely if hasattr passed, but check defensively
            logger.debug("Context request has 'query_params', but its value is None.")
            return {}

        # Check if query_params has an 'items' method (like a Starlette MultiDict)
        if not hasattr(query_params, 'items'):
            logger.warning(f"Context request 'query_params' found (type: {type(query_params)}), but it has no 'items' method.")
            return {}

        # Now it should be safe to call items() and build the dictionary
        try:
            # The actual conversion from MultiDict (or similar) to dict
            params_dict = {k: v for k, v in query_params.items()}
            if params_dict:
                logger.debug(f"Extracted query params via ctx.request: {params_dict}")
                return params_dict
            else:
                logger.debug("ctx.request.query_params.items() returned empty.")
                return {}
        except Exception as item_err:
             # Catch potential errors during the .items() call or dict comprehension
             logger.error(f"Error calling .items() or creating dict from query_params: {item_err}", exc_info=True)
             return {}

    except ImportError as import_err:
         # Handle case where chainlit.context might not be available
         logger.error(f"Failed to import chainlit.context: {import_err}. Cannot get query params via context.", exc_info=False) # Keep log cleaner
         return {}
    except Exception as e:
        # General catch-all for unexpected errors within this function
        logger.error(f"Unexpected error in get_url_query_params: {str(e)}", exc_info=True)
        return {}


@cl.on_message
async def on_message(message: cl.Message):
    """Process user messages."""
    logger.debug(f"Chainlit on_message received: {message.content[:50]}...") # Logger should work

    try:
        # Get user info from user session
        user_info = cl.user_session.get("user_info", {"id": None, "name": "Anonymous", "email": "anonymous@example.com"})
        session_data = cl.user_session.get("session_data")

        logger.info(f"Received query from {user_info.get('name', 'Anonymous')}: '{message.content[:50]}...'")

        # Log authentication status
        log_authentication_status(session_data) # Assumes this helper uses logging correctly

        # Get game state
        game_state = state_manager.get_state()
        if game_state is None:
            game_state = {}
            logger.warning("state_manager.get_state() returned None, using empty dict.")
        else:
            try:
                game_state_str = json.dumps(game_state)
                log_limit = 200
                logger.debug(f"Game state for API call: {game_state_str[:log_limit]}{'...' if len(game_state_str) > log_limit else ''}")
            except TypeError as e:
                logger.error(f"Could not serialize game state for logging: {e}")
                logger.debug(f"Game state type: {type(game_state)}")

        # Get and process conversation history
        conversation_history = cl.chat_context.to_openai()
        processed_history = process_conversation_history(conversation_history, max_interactions=5)
        if processed_history:
            logger.debug(f"Including {len(processed_history)} messages from conversation history.")

        # Process query using API
        try:
            response = await call_process_query_api( # Make sure this function uses logging
                query=message.content,
                game_state=game_state,
                user_info=user_info,
                session_data=session_data,
                chat_context=processed_history
            )

            if "error" in response:
                error_msg = response.get('error', 'Unknown error')
                logger.error(f"API error response: {error_msg}")
                # ... (rest of error handling as before) ...
                await cl.Message(content=f"Sorry, there was an error processing your query: {error_msg}", author="System").send()
                return

            answer = response.get("answer", "Sorry, I couldn't find an answer.")
            logger.info(f"Received answer (first 50 chars): {answer[:50]}...")

            # Extract thinking content (Keep this logic)
            thinking_pattern = r'<think>(.*?)</think>'
            thinking_matches = re.findall(thinking_pattern, answer, re.DOTALL)
            thinking_content = "\n".join(thinking_matches).strip() if thinking_matches else ""
            clean_answer = re.sub(thinking_pattern, '', answer, flags=re.DOTALL).strip()

            # Display thinking step if content exists
            if thinking_content:
                 logger.debug("Displaying thinking step.")
                 async with cl.Step(name="Thinking") as thinking_step:
                     # Ensure thinking_content is a string before streaming
                     await thinking_step.stream_token(str(thinking_content))
                     thinking_step.name = "Keenplay's Reasoning"
                     # await thinking_step.update() # Implicit update at end of block

            # Send the final answer
            if clean_answer:
                logger.debug("Sending final answer to UI.")
                await cl.Message(content=clean_answer).send()
            else:
                # Log if both thinking and answer are empty after processing
                if not thinking_content:
                     logger.warning("API returned an answer that was empty or only contained whitespace after removing <think> tags.")
                     await cl.Message(content="I processed your request, but the response was empty.").send()
                else:
                     # If there was thinking content but no main answer
                     logger.info("API response only contained thinking content, no separate answer.")
                     # UI already showed the thinking step, maybe add a small note?
                     # await cl.Message(content="(Thinking process displayed above)").send() # Optional clarity

            # Save chat history (Make sure save_chat_history uses logging)
            if user_info and user_info.get("id"):
                try:
                    user_id = user_info["id"] # Use the actual ID
                    save_chat_history(
                        user_id=user_id,
                        query=message.content,
                        response=clean_answer, # Save the cleaned answer
                        game_state=game_state, # Pass the retrieved game state
                        thinking_content=thinking_content # Pass extracted thinking
                    )
                    logger.info(f"Saved chat history for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving chat history: {str(e)}", exc_info=True)
            else:
                logger.warning("No user ID available, skipping chat history save.")

        except Exception as e:
            logger.error(f"Error during API call or response processing: {str(e)}", exc_info=True)
            await cl.Message(content="Sorry, an internal error occurred while processing your query.", author="System").send()

    except Exception as e:
        # Catch-all for unexpected errors in on_message
        logger.error(f"Critical error in on_message handler: {str(e)}", exc_info=True)
        await cl.Message(content="An unexpected error occurred. Please try again.", author="System").send()

# --- __main__ block (Keep for context, logging should work here too) ---
if __name__ == "__main__":
     # This block executes when chainlit runs this file directly.
     # Logging should be configured by the 'log_manager' import at the top.
     logger.info("Chainlit app module loaded directly by Chainlit CLI.")
     logger.info(f"API URL (from __main__): {PROCESS_QUERY_API_URL}")
     logger.info(f"State file path (from config): {config.state_file_path}")
     logger.info(f"Session Dir (from log_manager): {log_manager.session_dir}")

# --- End chainlit_app.py ---