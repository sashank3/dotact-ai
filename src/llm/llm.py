import logging
from src.llm.client.llm_client import LLMClient
from src.llm.prompt.prompt_builder import build_prompt


class LLMOrchestrator:
    """
    Orchestrates user query processing with LLM.
    """

    def __init__(self):
        self.client = LLMClient()

    def get_llm_response(self, user_query: str, context_data: str, stream=False):
        """
        Processes the query and gets a structured response from the LLM.
        - If stream=True, yields the response chunks while suppressing <THINKING>.
        - Otherwise, returns a dictionary with "thinking" and "response" fields.
        """
        logging.info("[LLM ORCHESTRATOR] Building messages for LLM...")

        messages = build_prompt(user_query, context_data)

        logging.info("[LLM ORCHESTRATOR] Sending chat completion request...")
        if stream:
            return self.client.generate_text(messages, stream=True)
        else:
            response_json = self.client.generate_text(messages)

            if not response_json.get("response"):
                logging.warning("[LLM ORCHESTRATOR] Empty response detected.")

            return response_json
