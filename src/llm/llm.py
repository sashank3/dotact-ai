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
        """Get complete LLM response in one call"""
        
        messages = build_prompt(user_query, context_data)
        response = self.client.generate_text(messages, stream=stream)
        
        if not response:
            logging.error("[LLM ORCHESTRATOR] Received empty response from LLM")
            return "I apologize, but I couldn't generate a response at this time."
            
        # Remove thinking notes if present
        if "<think>" in response and "</think>" in response:
            response = response.split("</think>")[1].strip()
            
        logging.info("[LLM ORCHESTRATOR] Response preview: %s...", response[:200])
        
        return response.strip()
