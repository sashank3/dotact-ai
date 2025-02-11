import logging
import json
from openai import OpenAI
from src.llm.config.llm_config import LLMConfig


class LLMClient:
    """
    A client that uses the Nebius-based OpenAI-like library for chat completions.
    """

    def __init__(self):
        self.api_key = LLMConfig.NEBIUS_API_KEY
        self.base_url = LLMConfig.BASE_URL
        self.model = LLMConfig.MODEL_NAME
        self.default_params = LLMConfig.DEFAULT_PARAMS

        # Initialize the Nebius "OpenAI" client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def generate_text(self, messages, **kwargs) -> str:
        """
        Calls the Nebius-based Chat Completions endpoint with the given messages.
        Returns the text from the first assistant message.

        'messages' should be a list of dicts, e.g.:
           [
             {"role": "system", "content": "..."},
             {"role": "user", "content": "..."}
           ]
        """

        # Merge default params with any function-level overrides
        params = {**self.default_params, **kwargs}

        logging.info("[LLM CLIENT] Sending chat completion request with params: %s", params)
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **params  # e.g. temperature=..., max_tokens=..., etc.
        )

        # According to the doc, you can do completion.to_json() or parse it
        completion_str = completion.to_json()
        # Typically the response includes: {"choices": [{"message": {"content": "..."} }]}
        completion_json = json.loads(completion_str)
        choices = completion_json.get("choices", [])
        if not choices:
            logging.warning("[LLM CLIENT] No 'choices' in completion. Full response: %s", completion_json)
            return "[No text returned]"

        # Grab the assistant's content from the first choice
        first_choice = choices[0]
        msg = first_choice.get("message", {})
        text_output = msg.get("content", "[No content in assistant's message]")
        return text_output
