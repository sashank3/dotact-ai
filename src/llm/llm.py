# src/llm/llm.py
import logging
from src.llm.client.llm_client import LLMClient
from src.llm.prompt.prompt_builder import build_prompt


class LLMOrchestrator:
    """
    High-level orchestrator that:
    1. Builds the 'messages' array from data sources (user query, GSI context).
    2. Calls the LLM client for a chat completion.
    3. Returns the final text response.
    """

    def __init__(self):
        self.client = LLMClient()

    def get_llm_response(self, user_query: str, context_data: str) -> str:
        """
        Builds messages from the user query + context,
        calls the LLM, returns the response.
        """
        logging.info("[LLM ORCHESTRATOR] Building messages for LLM...")

        # 1) Convert user query and context into a list of chat messages
        #    'build_prompt' can now return a list of dicts (system, user) or
        #    you can adapt it to return just user content, then build the array here.
        messages = build_prompt(user_query, context_data)

        # logging.info(f"DEBUG API KEY: {self.client.api_key}")

        # 2) Send messages to LLM
        logging.info("[LLM ORCHESTRATOR] Submitting chat completion request...")
        response_text = self.client.generate_text(messages)
        logging.info("[LLM ORCHESTRATOR] Received response from LLM.")

        return response_text
