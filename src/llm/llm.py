import logging
from src.llm.client.llm_client import LLMClient
from src.llm.prompt.prompt_builder import build_prompt


class LLMOrchestrator:
    """
    Orchestrates user query processing with LLM.
    """

    def __init__(self):
        self.client = LLMClient()

    def get_llm_response(self, user_query: str, context_data: str) -> str:
        """
        Processes the query and gets a response from the LLM.
        """
        logging.info("[LLM ORCHESTRATOR] Building messages for LLM...")

        # Construct messages for LLM
        messages = build_prompt(user_query, context_data)

        logging.info("[LLM ORCHESTRATOR] Sending chat completion request...")
        response_text = self.client.generate_text(messages)
        logging.info("[LLM ORCHESTRATOR] LLM Response received.")

        return response_text
