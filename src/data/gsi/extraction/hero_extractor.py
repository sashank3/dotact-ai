import logging

previous_enemy_heroes = set() # Module-level set to track previously seen enemy heroes

def extract_hero_lists(game_state: dict, state_manager_instance):
    """
    Extracts ally and enemy hero lists from the game state.
    Updates the ally_heroes and enemy_heroes sets in the provided StateManager instance.
    """
    global previous_enemy_heroes # Access the module-level set

    current_enemy_heroes_before_update = set(state_manager_instance.enemy_heroes) # Create a copy to compare later

    minimap_data = game_state.get("minimap", {})
    if minimap_data:
        for obj_key, obj_data in minimap_data.items():
            hero_name = obj_data.get("name")
            if hero_name:
                hero_name_cleaned = hero_name.replace("npc_dota_hero_", "")
                image_type = obj_data.get("image", "")

                if "herocircle_self" in image_type or "herocircle" in image_type: # Ally heroes
                    state_manager_instance.ally_heroes.add(hero_name_cleaned)
                elif image_type == "minimap_enemyicon": # Enemy heroes
                    state_manager_instance.enemy_heroes.add(hero_name_cleaned)

    if len(state_manager_instance.ally_heroes) + len(state_manager_instance.enemy_heroes) == 10:
        state_manager_instance.heroes_tracked = True
        logging.info(f"[HERO PROCESSOR] All 10 heroes found for match {state_manager_instance.current_match_id}. Tracking stopped. Allies: {state_manager_instance.ally_heroes}, Enemies: {state_manager_instance.enemy_heroes}")
    else:
        current_enemy_heroes_after_update = set(state_manager_instance.enemy_heroes)
        if len(current_enemy_heroes_after_update) > len(current_enemy_heroes_before_update): # New enemy hero detected
            logging.debug(f"[HERO PROCESSOR] New enemy hero detected for match {state_manager_instance.current_match_id}. Allies: {state_manager_instance.ally_heroes}, Enemies: {state_manager_instance.enemy_heroes}")

    previous_enemy_heroes = set(state_manager_instance.enemy_heroes) # Update previous_enemy_heroes for next iteration 