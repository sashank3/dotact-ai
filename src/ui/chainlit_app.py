import chainlit as cl
import datetime
import sys
import os
import logging

# Ensure Python can find src/...
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.global_config import GLOBAL_CONFIG
from src.data.gsi.processing.gsi_data_provider import get_processed_state
from src.llm.llm import LLMOrchestrator
from src.ui.components.history_manager import save_chat_history, load_chat_history

llm_orch = LLMOrchestrator()

@cl.on_chat_start
async def start():
    """Initialize chat and load past sessions."""
    cl.user_session.set("chat_history", load_chat_history())
    await cl.Message(
        content="🎮 Welcome to KeenMind, your Dota 2 Assistant! Ask me anything."
    ).send()
    await cl.sleep(0.1)


@cl.on_message
async def on_message(message: cl.Message):
    user_query = message.content
    logging.info("[CHAINLIT] Received user query: %s", user_query)

    # 1) Get processed game state & hero name
    game_state_text, hero_name = get_processed_state()
    logging.info("[CHAINLIT] Processed game state text: %s", game_state_text)
    logging.info("[CHAINLIT] Hero name: %s", hero_name)

    # 2) Show a short "loading" message so the user knows we're working
    await cl.Message(
        content=f"Player: {hero_name}. Analyzing current game..."
    ).send()
    await cl.sleep(0.1)

    try:
        # 3) Call your LLM (this is synchronous, so it blocks until done)
        response = llm_orch.get_llm_response(user_query, game_state_text)
        logging.info("[CHAINLIT] Sending response to UI")

        # 4) Send the LLM’s raw markdown so Chainlit renders headings, bullets, etc.
        await cl.Message(
            content=response  # Chainlit defaults to interpreting this as markdown
        ).send()
        await cl.sleep(0.1)

        # 5) Log & save chat history
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_entry = {
            "timestamp": timestamp,
            "hero": hero_name,
            "query": user_query,
            "game_state": game_state_text,
            "response": response
        }
        save_chat_history(chat_entry)
        logging.info("[CHAINLIT] Chat history saved")

    except Exception as e:
        # If an error occurs, show the error
        error_msg = f"Error generating response: {e}"
        logging.error("[CHAINLIT] %s", error_msg, exc_info=True)

        await cl.Message(content=f"❌ {error_msg}").send()
        await cl.sleep(0.1)
