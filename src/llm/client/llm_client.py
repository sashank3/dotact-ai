import os
import logging
import re
from openai import OpenAI
from src.global_config import GLOBAL_CONFIG


class LLMClient:
    """
    A client that interacts with the Nebius-based OpenAI-compatible API (DeepSeek R1).
    Manages streaming and parsing of responses to remove <think> sections.
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
        """
        Calls the LLM API with a chat completion request.
        If stream=True, returns a generator of tokens (str), skipping <think> content.
        Otherwise, returns a plain string with <think> removed.
        """
        params = {**self.default_params, **kwargs}

        logging.info("[LLM CLIENT] Sending chat completion request with params: %s", params)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            **params
        )

        if stream:
            return self._handle_streaming(response)
        else:
            return self._parse_response(response)

    def _parse_response(self, response):
        """Parses a non-streaming response and removes <think> sections."""
        # 'response.choices[0].message.content' is a string
        raw_text = response.choices[0].message.content or ""
        # Remove <think> ... </think> blocks
        text_no_think = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
        return text_no_think.strip()

    def _handle_streaming(self, response):
        """
        Handles streaming responses while skipping <think> sections.
        Yields only the final text chunks.
        """
        inside_think = False

        for chunk in response:
            if not chunk.choices:
                continue

            # The current token fragment
            text = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""

            # If <think> appears, start ignoring
            if "<think>" in text:
                inside_think = True
            # If </think> appears, stop ignoring
            if "</think>" in text:
                inside_think = False
                # Remove everything up to and including </think> from this chunk
                text = text.split("</think>", 1)[-1]

            if not inside_think and text:
                yield text
