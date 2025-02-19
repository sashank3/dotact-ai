import chainlit as cl
import datetime
from src.data.gsi.gsi import get_processed_gsi_data
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

    # 1) Grab the current game state
    game_state_text = get_processed_gsi_data()

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

    # 6) Optionally, save the final text to your history
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_entry = {
        "timestamp": timestamp,
        "hero": "Unknown Hero",  # or fetch from game_state
        "query": user_query,
        "response": full_text
    }
    save_chat_history(chat_entry)
