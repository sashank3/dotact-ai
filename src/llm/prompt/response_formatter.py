"""
Utility functions for formatting and displaying LLM responses.
"""

import logging


def display_response(response_json):
    """
    Nicely formats and prints the structured response from the LLM.
    Ensures clear separation of 'thinking', 'items', and 'game strategies'.
    """
    if not response_json or not isinstance(response_json, dict):
        logging.warning("[LLM RESPONSE FORMATTER] Invalid response format received.")
        print("⚠️ No valid response available.")
        return

    thinking = response_json.get("thinking", "No reasoning provided.")
    response = response_json.get("response", {})

    print("\n🔍 **Thinking Process:**")
    print(thinking)

    # Print Items Section
    items = response.get("items", [])
    if items:
        print("\n🛒 **Suggested Items:**")
        for item in items:
            print(f"- {item['name']}: {item['reason']}")

    # Print Game Strategies Section
    strategies = response.get("game_strategies", [])
    if strategies:
        print("\n🎯 **Game Strategies:**")
        for strategy in strategies:
            print(f"- {strategy['strategy']}: {strategy['reason']}")

    print("\n──────────────────────────────")


def process_llm_response(response_generator):
    """
    Handles streaming of LLM responses.
    - Skips streaming of <think>...</think> sections.
    - Only streams the actual response in real-time.
    """
    inside_think = False

    print("\n🎯 **Strategic Advice:**", end="", flush=True)

    for chunk in response_generator:
        if not chunk:
            continue

        if "<think>" in chunk:
            inside_think = True

        if inside_think:
            if "</think>" in chunk:
                inside_think = False
                chunk = chunk.split("</think>", 1)[-1]
            else:
                continue

        print(chunk, end="", flush=True)
