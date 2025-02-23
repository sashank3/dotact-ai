import os
import logging
from openai import OpenAI
from src.global_config import GLOBAL_CONFIG


class LLMClient:
    """
    A client that interacts with the Nebius-based OpenAI-compatible API (DeepSeek R1).
    """

    def __init__(self):
        llm_config = GLOBAL_CONFIG["llm"]

        self.api_key = llm_config.get("api_key", "None")
        self.api_key = self.api_key if self.api_key != "None" else os.getenv("NEBIUS_API_KEY")

        self.base_url = llm_config.get("base_url", "https://api.studio.nebius.ai/v1/")
        self.model = llm_config.get("model_name", "deepseek-ai/DeepSeek-R1")
        self.default_params = llm_config.get("default_params", {})

        # Initialize the OpenAI-compatible client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def generate_text(self, messages, stream=False, **kwargs):
        """Calls the LLM API with a chat completion request."""
        try:
            params = {**self.default_params, **kwargs}
            
            logging.info("[LLM CLIENT] Sending API request")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream,
                **params
            )
            
            if not response or not response.choices:
                logging.error("[LLM CLIENT] Empty response from API")
                return ""
            
            content = response.choices[0].message.content
            return content or ""
            
        except Exception as e:
            logging.error(f"[LLM CLIENT] Error generating response: {str(e)}")
            raise
