import logging

def convert_game_state_to_text(game_state: dict) -> tuple[str, str]:
    """
    Converts a raw game state dictionary into a readable text format and extracts hero name.
    Returns (formatted_text, hero_name)
    """
    if not game_state or not any(game_state.values()):
        logging.warning("[GSI PROCESSOR] Received empty or invalid game state")
        return "No game state available.", "Unknown Hero"

    # Extract hero name first
    hero = game_state.get("hero", {})
    hero_name = hero.get("name", "Unknown Hero").replace("npc_dota_hero_", "")

    text_output = []
    try:
        # Map info
        game_map = game_state.get("map", {})
        if game_map:
            text_output.append(
                f"Game State: {game_map.get('game_state', 'Unknown')}, "
                f"Match ID: {game_map.get('matchid', 'Unknown')}, "
                f"Game Time: {game_map.get('game_time', 0)}s, "
                f"Score: {game_map.get('radiant_score', 0)} - {game_map.get('dire_score', 0)}"
            )

        # Player info
        player = game_state.get("player", {})
        if player:
            text_output.append(
                f"Player: {player.get('name', 'Unknown')} "
                f"[Team: {player.get('team_name', 'Unknown')}, "
                f"K/D/A: {player.get('kills', 0)}/{player.get('deaths', 0)}/{player.get('assists', 0)}, "
                f"LH/DN: {player.get('last_hits', 0)}/{player.get('denies', 0)}, "
                f"GPM/XPM: {player.get('gpm', 0)}/{player.get('xpm', 0)}]"
            )

        # Hero info
        hero = game_state.get("hero", {})
        if hero:
            text_output.append(
                f"Hero: {hero.get('name', 'Unknown').replace('npc_dota_hero_', '')} "
                f"[Level {hero.get('level', 0)}, "
                f"HP: {hero.get('health', 0)}/{hero.get('max_health', 0)}, "
                f"MP: {hero.get('mana', 0)}/{hero.get('max_mana', 0)}]"
            )

        # Abilities
        abilities = game_state.get("abilities", {})
        if abilities:
            ability_texts = []
            for ability_key, ability_info in abilities.items():
                name = ability_info.get("name", "Unknown").replace(f"{hero.get('name', 'Unknown').split('npc_dota_hero_')[-1]}_", "")
                level = ability_info.get("level", 0)
                cooldown = ability_info.get("cooldown", 0)
                ability_texts.append(f"{name}(Lv{level}, CD:{cooldown})")
            if ability_texts:
                text_output.append(f"Abilities: {', '.join(ability_texts)}")

        # Items
        items = game_state.get("items", {})
        if items:
            item_texts = []
            for slot, item_info in items.items():
                if isinstance(item_info, dict) and item_info.get("name") != "empty":
                    name = item_info["name"].replace("item_", "")
                    charges = item_info.get("charges", 0)
                    item_text = f"{name}"
                    if charges > 0:
                        item_text += f"({charges})"
                    item_texts.append(item_text)
            if item_texts:
                text_output.append(f"Items: {', '.join(item_texts)}")

        # Buildings (only include if there are buildings)
        buildings = game_state.get("buildings", {})
        if buildings and any(buildings.values()):
            for team, team_buildings in buildings.items():
                building_texts = []
                for building_name, building_info in team_buildings.items():
                    health_percent = int((building_info.get("health", 0) / building_info.get("max_health", 1)) * 100)
                    building_texts.append(f"{building_name}({health_percent}%)")
                if building_texts:
                    text_output.append(f"{team.capitalize()} Buildings: {', '.join(building_texts)}")

    except Exception as e:
        logging.error(f"[GSI PROCESSOR] Error processing game state: {e}")
        return "Error processing game state.", hero_name

    formatted_text = "\n".join(text_output) if text_output else "No valid game state data available."
    logging.debug(f"[GSI PROCESSOR] Processed text: {formatted_text}")
    return formatted_text, hero_name
