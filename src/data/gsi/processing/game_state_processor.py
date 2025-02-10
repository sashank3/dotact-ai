import logging


def convert_game_state_to_text(game_state: dict) -> str:
    """
    Converts a raw game state dictionary into a more readable text format.
    """
    if not game_state:
        return "No game state available."

    # Extract key components
    game_map = game_state.get("map", {})
    player = game_state.get("player", {})
    hero = game_state.get("hero", {})
    abilities = game_state.get("abilities", {})
    items = game_state.get("items", {})
    buildings = game_state.get("buildings", {})
    draft = game_state.get("draft", {})

    # Build up text representation
    text_output = []

    # Map info
    text_output.append(
        f"Map: {game_map.get('name', 'Unknown')}, "
        f"Game State: {game_map.get('game_state', 'N/A')}, "
        f"Time: {game_map.get('game_time', '0')}s"
    )

    # Player info
    text_output.append(
        f"Player: {player.get('name', 'Unknown')} "
        f"[Gold: {player.get('gold', 0)}, "
        f"K/D/A: {player.get('kills', 0)}/"
        f"{player.get('deaths', 0)}/"
        f"{player.get('assists', 0)}]"
    )

    # Hero info
    text_output.append(
        f"Hero: {hero.get('name', 'Unknown')} "
        f"[HP: {hero.get('health', 0)}/"
        f"{hero.get('max_health', 0)}, "
        f"Mana: {hero.get('mana', 0)}/"
        f"{hero.get('max_mana', 0)}]"
    )

    # Abilities info
    ability_texts = []
    for _, ability_info in abilities.items():
        ability_name = ability_info.get("name", "Unknown")
        ability_level = ability_info.get("level", 0)
        ability_cd = ability_info.get("cooldown", 0)
        ability_texts.append(f"{ability_name}(Lv{ability_level}, CD={ability_cd})")
    if ability_texts:
        text_output.append(f"Abilities: {', '.join(ability_texts)}")

    # Items info
    item_names = []
    for _, item_info in items.items():
        item_name = item_info.get("name", "Unknown")
        if item_name != "empty":
            item_names.append(item_name)
    if item_names:
        text_output.append(f"Items: {', '.join(item_names)}")

    # Buildings summary (example)
    if buildings:
        # If 'buildings' is a dict of building objects, just do a count or a minimal summary
        text_output.append(f"Buildings: {len(buildings)} building entries")

    # Draft summary (example)
    if draft:
        # If 'draft' is a structure with picks/bans, you can parse them here
        text_output.append(f"Draft info: {draft}")

    # Combine into a single readable string
    formatted_text = "\n".join(text_output)
    logging.info(f"[GSI PREPROCESSOR] Formatted game state:\n{formatted_text}")
    return formatted_text
