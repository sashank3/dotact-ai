import chainlit as cl
import datetime
import sys
import os
import logging
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.global_config import GLOBAL_CONFIG
from src.data.gsi.gsi import get_processed_gsi_data, get_raw_gsi_data
from src.data.gsi.processing.game_state_processor import extract_hero_name
from src.llm.llm import LLMOrchestrator
from src.ui.components.history_manager import save_chat_history, load_chat_history

llm_orch = LLMOrchestrator()


@cl.on_chat_start
async def on_chat_start():
    """Initialize chat and load past sessions."""
    cl.user_session.set("chat_history", load_chat_history())
    await cl.Message(
        content="🎮 Welcome to your Dota 2 Assistant! Ask me anything."
    ).send()


@cl.on_message
async def on_message(message):
    user_query = message.content
    logging.info("[CHAINLIT] Received user query: %s", user_query)

    # 1) Read state from file instead of memory
    current_state = None
    try:
        with open(GLOBAL_CONFIG["data"]["gsi"]["state_file_path"], 'r') as f:
            current_state = json.load(f)
    except Exception as e:
        logging.warning(f"[CHAINLIT] Error loading game state: {e}")
    
    game_state_text = get_processed_gsi_data()
    
    hero_name = extract_hero_name(current_state) if current_state else "Unknown Hero"
    
    logging.info("[CHAINLIT] Current game state: %s", current_state)
    logging.info("[CHAINLIT] Processed game state text: %s", game_state_text)
    logging.info("[CHAINLIT] Extracted hero name: %s", hero_name)

    # 2) We want to stream tokens as they arrive
    token_stream = llm_orch.get_llm_response(user_query, game_state_text, stream=True)

    # 3) Create an initial message in Chainlit
    #    so we can progressively update it with partial tokens.
    final_msg = cl.Message(content="")
    await final_msg.send()

    # 4) Accumulate all tokens in a local buffer
    #    (so we can store them in chat history if you want)
    full_text = ""

    # 5) Stream the tokens to Chainlit
    for chunk in token_stream:
        full_text += chunk
        await final_msg.stream_token(chunk)

    # 6) Save the final text to history with hero information
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_entry = {
        "timestamp": timestamp,
        "hero": hero_name,
        "query": user_query,
        "response": full_text
    }
    logging.info("[CHAINLIT] Saving chat entry: %s", chat_entry)
    save_chat_history(chat_entry)
