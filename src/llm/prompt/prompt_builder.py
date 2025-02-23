def build_prompt(user_query: str, game_state_text: str):
    """
    Construct a structured list of messages for the Nebius chat endpoint.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are an expert Dota 2 assistant that provides highly relevant in-game advice. "
                "Format your response in markdown with two main sections:\n\n"
                "## Recommended Items\n"
                "• List 2-5 recommended items with explanations\n\n"
                "## Game Strategies\n"
                "• List 2-5 strategies based on the current game state\n\n"
                "Keep explanations clear and concise, prioritize high-impact recommendations, "
                "and ensure advice is immediately actionable based on the current game state."
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
