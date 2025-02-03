import logging


def handle_game_state(game_state):
    """
    Processes and logs incoming game state data.
    :param game_state: The dictionary representing the current game state.
    """
    try:
        # Access player and hero data
        player = game_state.get("player", {})
        hero = game_state.get("hero", {})
        abilities = hero.get("abilities", [])

        # Log player gold and hero health
        logging.info(f"Player Gold: {player.get('gold', 0)}")
        logging.info(f"Hero Health: {hero.get('health', 0)}/{hero.get('max_health', 0)}")

        # Log hero abilities
        for ability in abilities:
            name = ability.get("name", "Unknown")
            cooldown = ability.get("cooldown", 0)
            logging.info(f"Ability: {name} | Cooldown: {cooldown}s")

    except Exception as e:
        logging.error(f"Error processing game state: {e}")
