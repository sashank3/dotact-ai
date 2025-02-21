import logging
from src.llm.client.llm_client import LLMClient
from src.llm.prompt.prompt_builder import build_prompt


class LLMOrchestrator:
    """
    Orchestrates user query processing with the LLM.
    """

    def __init__(self):
        self.client = LLMClient()

    def get_llm_response(self, user_query: str, context_data: str, stream=False):
        """
        Build the prompt and get a response from the LLM.
        If stream=True, returns a generator of tokens (strings).
        Otherwise, returns a single string.
        """
        logging.info("[LLM ORCHESTRATOR] Processing query: %s", user_query)
        logging.info("[LLM ORCHESTRATOR] With context: %s", context_data)

        messages = build_prompt(user_query, context_data)
        logging.info("[LLM ORCHESTRATOR] Built messages: %s", messages)

        logging.info("[LLM ORCHESTRATOR] Sending chat completion request...")
        result = self.client.generate_text(messages, stream=stream)

        if not stream:
            logging.info("[LLM ORCHESTRATOR] Generated response: %s", result)
        
        return result
