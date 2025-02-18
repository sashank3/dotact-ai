import os
import logging
import re
from openai import OpenAI
from src.config.global_config import GLOBAL_CONFIG


class LLMClient:
    """
    A client that interacts with the Nebius-based OpenAI-compatible API.
    Manages streaming and parsing of responses to separate 'thinking' from the actual response.
    """

    def __init__(self):
        llm_config = GLOBAL_CONFIG["llm"]

        self.api_key = llm_config.get("api_key", "None")
        self.api_key = self.api_key if self.api_key != "None" else os.getenv("NEBIUS_API_KEY")

        self.base_url = llm_config.get("base_url", "https://api.studio.nebius.ai/v1/")
        self.model = llm_config.get("model_name", "deepseek-ai/DeepSeek-R1")
        self.default_params = llm_config.get("default_params", {})

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def generate_text(self, messages, stream=False, **kwargs):
        """
        Calls the LLM API with a chat completion request.
        Handles streaming while extracting <think> content separately.
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
        """
        Parses a non-streaming response and extracts <think> sections.
        """
        raw_text = response.choices[0].message.get("content", "")

        thinking_text, response_text = self._extract_sections(raw_text)
        return {"thinking": thinking_text, "response": response_text}

    def _handle_streaming(self, response):
        """
        Handles streaming responses while skipping the <think> section.
        """
        inside_think = False

        for chunk in response:
            if not chunk.choices:
                continue

            text = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""

            if "<think>" in text:
                inside_think = True
            if "</think>" in text:
                inside_think = False
                text = text.split("</think>", 1)[-1]  # Remove the </think> tag

            if not inside_think:
                yield text

    @staticmethod
    def _extract_sections(text):
        """
        Extracts <think> and response sections from the text using regex.
        """
        thinking_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)

        thinking_text = thinking_match.group(1).strip() if thinking_match else ""
        response_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        return thinking_text, response_text
