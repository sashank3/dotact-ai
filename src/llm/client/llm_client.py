import os
import logging
import json
from openai import OpenAI
from src.config.global_config import GLOBAL_CONFIG


class LLMClient:
    """
    A client that interacts with the Nebius-based OpenAI-compatible API.
    """

    def __init__(self):
        llm_config = GLOBAL_CONFIG["llm"]

        # API key (override with ENV if set)
        self.api_key = llm_config.get("api_key", "None")
        self.api_key = self.api_key if self.api_key != "None" else os.getenv("NEBIUS_API_KEY")

        self.base_url = llm_config.get("base_url", "https://api.studio.nebius.ai/v1/")
        self.model = llm_config.get("model_name", "deepseek-ai/DeepSeek-R1")
        self.default_params = llm_config.get("default_params", {})

        # Initialize the Nebius "OpenAI" client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def generate_text(self, messages, **kwargs) -> str:
        """
        Calls the LLM API with chat completion request.
        """

        # Merge default params with overrides
        params = {**self.default_params, **kwargs}

        logging.info("[LLM CLIENT] Sending chat completion request with params: %s", params)
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **params
        )

        completion_str = completion.to_json()
        completion_json = json.loads(completion_str)
        choices = completion_json.get("choices", [])

        if not choices:
            logging.warning("[LLM CLIENT] No 'choices' returned. Full response: %s", completion_json)
            return "[No text returned]"

        return choices[0].get("message", {}).get("content", "[No content in response]")
