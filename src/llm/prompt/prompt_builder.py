def build_prompt(user_query: str, game_state_text: str):
    """
    Construct a structured list of messages for the Nebius chat endpoint.
    Ensures clear separation of the model's reasoning and final response.
    """

    return [
        {
            "role": "system",
            "content": (
                "You are an expert Dota 2 assistant that provides highly relevant in-game advice. "
                "Your response must strictly follow this structured format:\n\n"
                "{\n"
                '  "items": [\n'
                '      {"name": "Item Name", "reason": "Short explanation of why this item is good and how to use it."},\n'
                '      ... (repeat for 2-5 items depending on options available)\n'
                '  ],\n'
                '  "game_strategies": [\n'
                '      {"strategy": "Strategy Name", "reason": "Short explanation of why this strategy is good and how to execute it."},\n'
                '      ... (repeat for 2-5 strategies depending on the game context)\n'
                '  ]\n'
                "}\n"
                "**IMPORTANT RULES:**\n"
                "- Do not include markdown, extra text, or explanations outside of these sections.\n"
                "- Keep explanations clear, concise (2-4 sentences per item/strategy).\n"
                "- Prioritize **high-impact** recommendations based on the player's situation.\n"
                "- Do NOT suggest redundant or generic advice.\n"
                "- Ensure your response is always **actionable and useful** for real gameplay.\n\n"
                "Now, analyze the provided game state and generate your response."
            )
        },
        {
            "role": "user",
            "content": (
                f"Game Context:\n{game_state_text}\n\n"
                f"Player Query: {user_query}\n"
            )
        }
    ]
