def build_prompt(user_query: str, game_state_text: str):
    """
    Construct a list of messages to feed to the Nebius chat endpoint.
    We can embed the game state in a system or user message.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are an expert Dota 2 assistant. "
                "Use the following game context to help the player:\n\n"
                f"{game_state_text}\n\n"
                "Provide top-tier strategic advice."
            )
        },
        {
            "role": "user",
            "content": user_query
        }
    ]
