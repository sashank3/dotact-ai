import json
import os
import logging
import boto3
import requests
import base64
from botocore.exceptions import ClientError
import traceback
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            return json.loads(base64.b64decode(response['SecretBinary']))
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")
        raise e

def convert_game_state_to_text(game_state):
    """
    Converts a raw game state dictionary into a readable text format and extracts hero name.
    Returns (formatted_text, hero_name)
    """
    if not game_state or not any(game_state.values()):
        logger.warning("Received empty or invalid game state")
        return "No game state available.", "Unknown Hero"

    # Extract hero name first
    hero = game_state.get("hero", {})
    hero_name = hero.get("name", "Unknown Hero").replace("npc_dota_hero_", "")

    text_output = []
    try:
        # Order information from less important to more important
        # Basic game state information
        text_output.append(_process_map_data(game_state.get("map", {})))
        text_output.append(_process_buildings_data(game_state.get("buildings", {})))
        
        # Player stats 
        text_output.append(_process_player_data(game_state.get("player", {})))
        
        # Item information
        text_output.append(_process_items_data(game_state.get("items", {})))
        
        # Hero-specific information (more important)
        text_output.append(_process_hero_data(game_state.get("hero", {})))
        text_output.append(_process_abilities_data(game_state.get("abilities", {}), hero))
        
        # Most important strategic information (placed last for context proximity)
        text_output.append(_process_ward_and_location_data(game_state.get("minimap", {})))
        text_output.append(_process_hero_lists_data(game_state.get("allies", []), game_state.get("enemies", [])))

    except Exception as e:
        logger.error(f"Error processing game state: {e}")
        return "Error processing game state.", hero_name

    # Filter out any empty strings and join with newline
    formatted_text_lines = [line for line in text_output if line]
    formatted_text = "\n".join(formatted_text_lines) if formatted_text_lines else "No valid game state data available."

    # Add a clear header to help the LLM identify the game state information
    formatted_text = "=== DOTA 2 GAME STATE ===\n" + formatted_text

    logger.debug(f"Processed text: {formatted_text}")
    return formatted_text, hero_name

def _process_map_data(map_data):
    """Processes map data and returns formatted text."""
    if not map_data:
        return ""
    return (
        f"Game State: {map_data.get('game_state', 'Unknown')}, "
        f"Match ID: {map_data.get('matchid', 'Unknown')}, "
        f"Game Time: {map_data.get('game_time', 0)}s, "
        f"Score: {map_data.get('radiant_score', 0)} - {map_data.get('dire_score', 0)}"
    )

def _process_player_data(player_data):
    """Processes player data and returns formatted text."""
    if not player_data:
        return ""
    return (
        f"Player: {player_data.get('name', 'Unknown')} "
        f"[Team: {player_data.get('team_name', 'Unknown')}, "
        f"K/D/A: {player_data.get('kills', 0)}/{player_data.get('deaths', 0)}/{player_data.get('assists', 0)}, "
        f"LH/DN: {player_data.get('last_hits', 0)}/{player_data.get('denies', 0)}, "
        f"GPM/XPM: {player_data.get('gpm', 0)}/{player_data.get('xpm', 0)}]"
    )

def _process_hero_data(hero_data):
    """Processes hero data and returns formatted text."""
    if not hero_data:
        return ""
    return (
        f"Hero: {hero_data.get('name', 'Unknown').replace('npc_dota_hero_', '')} "
        f"[Level {hero_data.get('level', 0)}, "
        f"HP: {hero_data.get('health', 0)}/{hero_data.get('max_health', 0)}, "
        f"MP: {hero_data.get('mana', 0)}/{hero_data.get('max_mana', 0)}]"
    )

def _process_abilities_data(abilities_data, hero_data):
    """Processes abilities data and returns formatted text."""
    if not abilities_data:
        return ""
    ability_texts = []
    for ability_key, ability_info in abilities_data.items():
        hero_name_part = hero_data.get('name', 'Unknown').split('npc_dota_hero_')[-1] if hero_data else "Unknown"
        name = ability_info.get("name", "Unknown").replace(f"{hero_name_part}_", "")
        level = ability_info.get("level", 0)
        cooldown = ability_info.get("cooldown", 0)
        ability_texts.append(f"{name}(Lv{level}, CD:{cooldown})")
    return f"Abilities: {', '.join(ability_texts)}" if ability_texts else ""

def _process_items_data(items_data):
    """Processes items data and returns formatted text."""
    if not items_data:
        return ""
    item_texts = []
    for slot, item_info in items_data.items():
        if isinstance(item_info, dict) and item_info.get("name") != "empty":
            name = item_info["name"].replace("item_", "")
            charges = item_info.get("charges", 0)
            item_text = f"{name}"
            if charges > 0:
                item_text += f"({charges})"
            item_texts.append(item_text)
    return f"Items: {', '.join(item_texts)}" if item_texts else ""

def _process_buildings_data(buildings_data):
    """Processes buildings data and returns formatted text."""
    if not buildings_data or not any(buildings_data.values()):
        return ""
    building_output = []
    for team, team_buildings in buildings_data.items():
        building_texts = []
        for building_name, building_info in team_buildings.items():
            health_percent = int((building_info.get("health", 0) / building_info.get("max_health", 1)) * 100)
            building_texts.append(f"{building_name}({health_percent}%)")
        if building_texts:
            building_output.append(f"{team.capitalize()} Buildings: {', '.join(building_texts)}")
    return "\n".join(building_output) if building_output else ""

def _process_hero_lists_data(allies, enemies):
    """Processes ally and enemy hero lists and returns formatted text."""
    output_lines = []
    if allies:
        output_lines.append(f"Allies: {', '.join(allies)}")
    if enemies:
        output_lines.append(f"Enemies: {', '.join(enemies)}")
    return "\n".join(output_lines) if output_lines else ""

def _process_ward_and_location_data(minimap_data):
    """
    Processes minimap data to determine hero and ward locations relative to landmarks.
    Also counts observer and sentry wards.
    Returns a formatted string describing locations and ward counts.
    """
    if not minimap_data:
        return ""

    # --- Helper function for calculating distances and find closest location ---
    def distance(x1, y1, x2, y2):
        return ((x1 - x2)**2 + (y1 - y2)**2)**0.5
    
    def find_closest_landmark(x, y, landmarks):
        closest_landmark = None
        min_distance = float('inf')
        
        for name, (landmark_x, landmark_y) in landmarks.items():
            dist = distance(x, y, landmark_x, landmark_y)
            if dist < min_distance:
                min_distance = dist
                closest_landmark = name
        
        if closest_landmark is None:
            return "an unknown location", "Unknown"

        # Determine relative direction
        dx = x - landmarks[closest_landmark][0]
        dy = y - landmarks[closest_landmark][1]

        if abs(dx) > abs(dy): # More horizontal than vertical
            if dx > 0:
                direction = "east of"
            else:
                direction = "west of"
        else:               # More vertical than horizontal or equal
            if dy > 0:
                direction = "north of"
            else:
                direction = "south of"
        return f"{closest_landmark}", direction

    # --- Define Landmarks ---
    landmarks = {
        "Radiant Top T1": (-6336, 1856),
        "Radiant Top T2": (-6288, -872),
        "Radiant Top T3": (-6592, -3408),
        "Radiant Mid T1": (-1544, -1408),
        "Radiant Mid T2": (-3336, -2791),
        "Radiant Mid T3": (-4640, -4144),
        "Radiant Bot T1": (4924, -6080),
        "Radiant Bot T2": (-360, -6256),
        "Radiant Bot T3": (-3952, -6112),
        "Radiant Top Rax": (-6336, -3758),
        "Radiant Mid Rax": (-4672, -4552),
        "Radiant Bot Rax": (-4280, -6360),
        "Radiant Ancient": (-5920, -5352),
        "Radiant Fountain": (-7456, -6938),
        "Dire Top T1": (-4672, 6016),
        "Dire Top T2": (-128, 6016),
        "Dire Top T3": (3552, 5776),
        "Dire Mid T1": (524, 652),
        "Dire Mid T2": (2496, 2112),
        "Dire Mid T3": (4272, 3759),
        "Dire Bot T1": (6269, -2240),
        "Dire Bot T2": (6400, 384),
        "Dire Bot T3": (6336, 3032),
        "Dire Top Rax": (3898, 5496),
        "Dire Mid Rax": (4336, 4183),
        "Dire Bot Rax": (6592, 3392),
        "Dire Ancient": (5528, 5000),
        "Dire Fountain": (7408, 6848),
        "Top Powerup Rune Spawn": (-6800, 2400),
        "Bot Powerup Rune Spawn": (6800, -2600),
        "Top Radiant Secret Shop": (-5080, 1947),
        "Bot Radiant Secret Shop": (-6860, -5262),
        "Top Dire Secret Shop": (5360, 5384),
        "Bot Dire Secret Shop": (4886, -1207),
        "Radiant Outpost Top": (-4096, -448),
        "Radiant Outpost Bot": (3392, -448),
        "Dire Outpost Top": (-3332, 35),
        "Dire Outpost Bot": (4068, -868),
        "Roshan": (2900, 2600),
        "Top Lotus Pool": (-7682, 4419),
        "Bot Lotus Pool" : (8007, -4996),
        "Top Twin Gate": (-7488, 6912),
        "Bot Twin Gate": (7360, -6528)
    }

    # Process all heroes and wards from minimap data
    location_descriptions = []
    observer_ward_count = 0
    sentry_ward_count = 0
    
    # Find all heroes and wards on the minimap
    for obj_key, obj_data in minimap_data.items():
        image_type = obj_data.get("image", "")
        unitname = obj_data.get("unitname", "")
        x_pos = obj_data.get("xpos")
        y_pos = obj_data.get("ypos")
        
        # Skip objects without position data
        if x_pos is None or y_pos is None:
            continue
            
        # Process player hero (has special image type)
        if "herocircle_self" in image_type:
            closest_landmark, direction = find_closest_landmark(x_pos, y_pos, landmarks)
            location_descriptions.append(f"Hero is {direction} {closest_landmark}.")
            
        # Process ally heroes (not self)
        elif "herocircle" in image_type:
            hero_name = obj_data.get("name", "").replace("npc_dota_hero_", "")
            closest_landmark, direction = find_closest_landmark(x_pos, y_pos, landmarks)
            location_descriptions.append(f"{hero_name.capitalize()} is {direction} {closest_landmark}.")
            
        # Process and count wards
        if unitname == "npc_dota_observer_wards":
            observer_ward_count += 1
            closest_landmark, direction = find_closest_landmark(x_pos, y_pos, landmarks)
            location_descriptions.append(f"Observer ward {direction} {closest_landmark}.")
        elif unitname == "npc_dota_sentry_wards":
            sentry_ward_count += 1
            closest_landmark, direction = find_closest_landmark(x_pos, y_pos, landmarks)
            location_descriptions.append(f"Sentry ward {direction} {closest_landmark}.")

    # Add ward count summary at the beginning
    if observer_ward_count > 0 or sentry_ward_count > 0:
        location_descriptions.insert(0, f"Ward Summary: Observer({observer_ward_count}), Sentry({sentry_ward_count})")

    return "\n".join(location_descriptions)

def build_prompt(user_query, game_state_text):
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

def get_llm_response(query, game_state_text):
    """Generate a response using the Nebius LLM API"""
    try:
        # Get API key from Secrets Manager
        secrets = get_secret(os.environ.get('LLM_SECRET_NAME', 'keenmind/LLMCredentials'))
        api_key = secrets.get('API_KEY')
        
        if not api_key:
            logger.error("No API key found in secrets")
            return "Error: LLM API key not configured properly."
        
        # Build the prompt using the prompt builder
        messages = build_prompt(query, game_state_text)
        
        # Use Nebius API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Nebius API endpoint
        nebius_endpoint = "https://llm.api.cloud.nebius.ai/v1/chat/completions"
        
        logger.info(f"Sending request to Nebius API with query: {query}")
        
        payload = {
            "messages": messages,
            "model": "yandex/yandexgpt",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            nebius_endpoint,
            headers=headers,
            json=payload,
            timeout=25  # Set timeout to avoid Lambda timeout issues
        )
        
        if response.status_code != 200:
            logger.error(f"Nebius API error: {response.status_code} - {response.text}")
            return f"Error from LLM API: {response.status_code}"
        
        response_json = response.json()
        logger.info("Successfully received response from Nebius API")
        
        # Extract the content from the response
        return response_json['choices'][0]['message']['content']
        
    except requests.exceptions.Timeout:
        logger.error("Request to Nebius API timed out")
        return "Error: LLM request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return f"Error connecting to LLM API: {str(e)}"
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return f"Error generating response: {str(e)}"

def process_query(query, game_state, user_info):
    """
    Process a user query with the provided game state.
    
    Args:
        query (str): The user's query
        game_state (dict): The current game state
        user_info (dict): Information about the user
        
    Returns:
        dict: The processed result with the answer
    """
    try:
        print(f"Processing query: {query}")
        
        # Check if game state is empty
        if not game_state or not isinstance(game_state, dict):
            print("Warning: Empty or invalid game state")
            game_state = {}
        
        # Extract relevant information from game state
        game_state_summary = extract_game_state_summary(game_state)
        print(f"Extracted game state summary with keys: {list(game_state_summary.keys())}")
        
        # Get LLM API key from Secrets Manager
        llm_api_key = get_api_key_from_secrets()
        if not llm_api_key:
            error_message = "Failed to retrieve LLM API key"
            print(error_message)
            return {
                "error": error_message,
                "status": "error"
            }
        
        # Construct prompt for the LLM
        prompt = construct_prompt(query, game_state_summary, user_info)
        print(f"Constructed prompt of length: {len(prompt)}")
        
        # Call the LLM API
        llm_response = call_llm_api(prompt, llm_api_key)
        
        # Check for errors in LLM response
        if "error" in llm_response:
            error_message = f"LLM API error: {llm_response['error']}"
            print(error_message)
            return {
                "error": error_message,
                "status": "error"
            }
        
        # Process and format the LLM response
        answer = process_llm_response(llm_response)
        print(f"Processed LLM response of length: {len(answer)}")
        
        # Return the result
        return {
            "answer": answer,
            "status": "success",
            "game_state_summary": {
                "hero": game_state_summary.get("hero", {}),
                "map": game_state_summary.get("map", {}),
                "allies": game_state_summary.get("allies", []),
                "enemies": game_state_summary.get("enemies", [])
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return {
            "error": error_message,
            "status": "error"
        }

def extract_game_state_summary(game_state):
    """
    Extract a summary of the game state for use in the LLM prompt.
    
    Args:
        game_state (dict): The full game state
        
    Returns:
        dict: A summary of the game state
    """
    summary = {}
    
    # Extract hero information
    if "hero" in game_state:
        hero_data = game_state.get("hero", {})
        summary["hero"] = {
            "name": hero_data.get("name", "Unknown").replace("npc_dota_hero_", ""),
            "level": hero_data.get("level", 0),
            "health": hero_data.get("health", 0),
            "health_max": hero_data.get("health_max", 0),
            "mana": hero_data.get("mana", 0),
            "mana_max": hero_data.get("mana_max", 0)
        }
    
    # Extract ally and enemy heroes (these are already processed by state_manager.py)
    summary["allies"] = game_state.get("allies", [])
    summary["enemies"] = game_state.get("enemies", [])
    
    # Extract map information
    if "map" in game_state:
        map_data = game_state.get("map", {})
        summary["map"] = {
            "game_time": map_data.get("game_time", 0),
            "game_state": map_data.get("game_state", "Unknown"),
            "match_id": map_data.get("matchid", "Unknown"),
            "win_team": map_data.get("win_team", "Unknown"),
            "radiant_score": map_data.get("radiant_score", 0),
            "dire_score": map_data.get("dire_score", 0)
        }
    
    # Extract items
    if "items" in game_state:
        items_data = game_state.get("items", {})
        summary["items"] = []
        
        for slot, item in items_data.items():
            if isinstance(item, dict) and "name" in item:
                summary["items"].append({
                    "name": item.get("name", "Unknown").replace("item_", ""),
                    "purchaser": item.get("purchaser", None),
                    "can_cast": item.get("can_cast", False),
                    "cooldown": item.get("cooldown", 0),
                    "charges": item.get("charges", 0)
                })
    
    # Extract abilities
    if "abilities" in game_state:
        abilities_data = game_state.get("abilities", {})
        summary["abilities"] = []
        
        for slot, ability in abilities_data.items():
            if isinstance(ability, dict) and "name" in ability:
                summary["abilities"].append({
                    "name": ability.get("name", "Unknown").replace("ability_", ""),
                    "level": ability.get("level", 0),
                    "can_cast": ability.get("can_cast", False),
                    "cooldown": ability.get("cooldown", 0),
                    "ultimate": ability.get("ultimate", False)
                })
    
    # Extract player information
    if "player" in game_state:
        player_data = game_state.get("player", {})
        summary["player"] = {
            "team": player_data.get("team_name", "Unknown"),
            "gold": player_data.get("gold", 0),
            "gold_reliable": player_data.get("gold_reliable", 0),
            "gold_unreliable": player_data.get("gold_unreliable", 0),
            "gpm": player_data.get("gpm", 0),
            "xpm": player_data.get("xpm", 0)
        }
    
    # Extract minimap information for ward locations
    if "minimap" in game_state:
        minimap_data = game_state.get("minimap", {})
        wards = []
        
        for obj_key, obj_data in minimap_data.items():
            if isinstance(obj_data, dict) and "image" in obj_data:
                image_type = obj_data.get("image", "")
                if "ward" in image_type:
                    wards.append({
                        "type": image_type,
                        "position_x": obj_data.get("position_x", 0),
                        "position_y": obj_data.get("position_y", 0),
                        "team": "ally" if "ally" in image_type else "enemy"
                    })
        
        if wards:
            summary["wards"] = wards
    
    return summary

def get_api_key_from_secrets():
    """
    Get the LLM API key from AWS Secrets Manager.
    
    Returns:
        str: The API key
    """
    try:
        # Initialize Secrets Manager client
        secrets_client = boto3.client('secretsmanager')
        
        # Get the secret - use environment variable or default to 'LLMCredentials'
        secret_name = os.environ.get('SECRETS_NAME', 'LLMCredentials')
        print(f"Looking for secret: {secret_name}")
        
        response = secrets_client.get_secret_value(
            SecretId=secret_name
        )
        
        # Parse the secret
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            
            # Try different possible key names
            for key_name in ['NEBIUS_API_KEY', 'LLM_API_KEY', 'API_KEY', 'api_key', 'nebius_api_key']:
                if key_name in secret:
                    print(f"Found API key with name: {key_name}")
                    return secret[key_name]
            
            # If we get here, we didn't find a recognized key
            print("API key not found in expected format. Available keys:", list(secret.keys()))
            
            # If there's only one key in the secret, use that
            if len(secret) == 1:
                only_key = list(secret.values())[0]
                print("Using the only available key in the secret")
                return only_key
                
            # As a fallback, try to use the first string value
            for key, value in secret.items():
                if isinstance(value, str) and value.startswith("ey"):  # JWT tokens often start with "ey"
                    print(f"Using key that looks like a JWT token: {key}")
                    return value
        
        print("API key not found in Secrets Manager")
        
        # Fallback to environment variable if available
        env_api_key = os.environ.get('NEBIUS_API_KEY')
        if env_api_key:
            print("Using API key from environment variable")
            return env_api_key
            
        return None
        
    except Exception as e:
        print(f"Error getting API key from Secrets Manager: {str(e)}")
        print(traceback.format_exc())
        
        # Fallback to environment variable if available
        env_api_key = os.environ.get('NEBIUS_API_KEY')
        if env_api_key:
            print("Using API key from environment variable after Secrets Manager error")
            return env_api_key
            
        return None

def construct_prompt(query, game_state_summary, user_info):
    """
    Construct a prompt for the LLM based on the query and game state.
    
    Args:
        query (str): The user's query
        game_state_summary (dict): Summary of the game state
        user_info (dict): Information about the user
        
    Returns:
        str: The constructed prompt
    """
    # Format the game state summary as a string
    game_state_text = format_game_state_for_prompt(game_state_summary)
    
    # Construct the prompt
    prompt = f"""
As Keenmind, a Dota 2 assistant, please help with the following query based on the current game state:

CURRENT GAME STATE:
{game_state_text}

USER QUERY:
{query}

Please provide a helpful, accurate, and concise response focused specifically on answering the query based on the game state information provided.
"""
    
    return prompt

def format_game_state_for_prompt(game_state_summary):
    """
    Format the game state summary in a more readable way for the prompt.
    
    Args:
        game_state_summary (dict): The game state summary
        
    Returns:
        str: Formatted game state text
    """
    sections = []
    
    # Add map information
    if "map" in game_state_summary:
        map_data = game_state_summary["map"]
        game_time_minutes = int(map_data.get("game_time", 0)) // 60
        game_time_seconds = int(map_data.get("game_time", 0)) % 60
        
        map_section = f"GAME INFO:\n"
        map_section += f"- Game Time: {game_time_minutes}:{game_time_seconds:02d}\n"
        map_section += f"- Game State: {map_data.get('game_state', 'Unknown')}\n"
        map_section += f"- Match ID: {map_data.get('match_id', 'Unknown')}\n"
        
        if map_data.get('win_team') != "Unknown":
            map_section += f"- Winning Team: {map_data.get('win_team')}\n"
            
        sections.append(map_section)
    
    # Add hero information
    if "hero" in game_state_summary:
        hero_data = game_state_summary["hero"]
        hero_name = hero_data.get("name", "Unknown").replace("_", " ").title()
        
        hero_section = f"PLAYER HERO - {hero_name}:\n"
        hero_section += f"- Level: {hero_data.get('level', 0)}\n"
        hero_section += f"- Health: {hero_data.get('health', 0)}/{hero_data.get('health_max', 0)}\n"
        hero_section += f"- Mana: {hero_data.get('mana', 0)}/{hero_data.get('mana_max', 0)}\n"
        
        sections.append(hero_section)
    
    # Add abilities
    if "abilities" in game_state_summary and game_state_summary["abilities"]:
        abilities = game_state_summary["abilities"]
        
        abilities_section = "ABILITIES:\n"
        for ability in abilities:
            ability_name = ability.get("name", "Unknown").replace("_", " ").title()
            ability_level = ability.get("level", 0)
            cooldown = ability.get("cooldown", 0)
            
            status = "Ready" if ability.get("can_cast", False) else f"Cooldown: {cooldown}s"
            abilities_section += f"- {ability_name} (Level {ability_level}): {status}\n"
            
        sections.append(abilities_section)
    
    # Add items
    if "items" in game_state_summary and game_state_summary["items"]:
        items = game_state_summary["items"]
        
        items_section = "ITEMS:\n"
        for item in items:
            item_name = item.get("name", "Unknown").replace("_", " ").title()
            charges = item.get("charges", 0)
            cooldown = item.get("cooldown", 0)
            
            item_info = f"- {item_name}"
            if charges > 0:
                item_info += f" ({charges} charges)"
            if cooldown > 0:
                item_info += f" (Cooldown: {cooldown}s)"
                
            items_section += f"{item_info}\n"
            
        sections.append(items_section)
    
    # Add ally and enemy heroes
    allies = game_state_summary.get("allies", [])
    enemies = game_state_summary.get("enemies", [])
    
    if allies:
        allies_formatted = [name.replace("_", " ").title() for name in allies]
        sections.append(f"ALLY HEROES: {', '.join(allies_formatted)}")
    
    if enemies:
        enemies_formatted = [name.replace("_", " ").title() for name in enemies]
        sections.append(f"ENEMY HEROES: {', '.join(enemies_formatted)}")
    
    # Combine all sections
    return "\n\n".join(sections)

def call_llm_api(prompt, api_key):
    """
    Call the LLM API with the constructed prompt.
    
    Args:
        prompt (str): The prompt for the LLM
        api_key (str): The API key for the LLM
        
    Returns:
        dict: The LLM response
    """
    try:
        if not api_key:
            print("No API key available")
            return {"error": "No API key available"}
        
        # Set up the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Configure for DeepSeek R1 model
        base_url = "https://api.studio.nebius.ai/v1/"
        model_name = "deepseek-ai/DeepSeek-R1"
        
        # Prepare messages in the format expected by DeepSeek R1
        messages = [
            {"role": "system", "content": "You are Keenmind, a helpful Dota 2 assistant that provides accurate and concise advice based on the current game state."},
            {"role": "user", "content": prompt}
        ]
        
        # Set default parameters
        params = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": False
        }
        
        # Make the API request
        endpoint = f"{base_url}chat/completions"
        print(f"Calling LLM API at: {endpoint}")
        print(f"Using model: {model_name}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=params,
            timeout=60  # Increased timeout for longer responses
        )
        
        # Check for errors
        if response.status_code != 200:
            error_message = f"LLM API error: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message}
        
        # Parse the response
        return response.json()
        
    except Exception as e:
        error_message = f"Error calling LLM API: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return {"error": error_message}

def process_llm_response(llm_response):
    """
    Process and format the LLM response.
    
    Args:
        llm_response (dict): The raw LLM response
        
    Returns:
        str: The processed answer
    """
    try:
        # Check for errors
        if "error" in llm_response:
            return f"Error from LLM: {llm_response['error']}"
        
        # Extract the answer from the response (DeepSeek R1 format)
        if "choices" in llm_response and len(llm_response["choices"]) > 0:
            message = llm_response["choices"][0].get("message", {})
            content = message.get("content", "")
            
            # Log token usage if available
            if "usage" in llm_response:
                usage = llm_response["usage"]
                print(f"Token usage - Prompt: {usage.get('prompt_tokens', 0)}, Completion: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
            
            return content
        
        return "No response from LLM"
        
    except Exception as e:
        print(f"Error processing LLM response: {str(e)}")
        return f"Error processing LLM response: {str(e)}"

def handler(event, context):
    """
    Lambda handler for processing Dota 2 queries.
    
    Args:
        event (dict): The Lambda event containing the request data
        context: The Lambda context
        
    Returns:
        dict: The response containing the answer to the query
    """
    try:
        # Log the event for debugging
        print(f"Received event: {json.dumps(event)[:500]}...")
        
        # Extract request data
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Extract query, game state, and user info
        query = body.get('query', '')
        game_state = body.get('game_state', {})
        user_info = body.get('user_info', {})
        
        # Log the extracted data
        print(f"Extracted query: {query}")
        print(f"Game state keys: {list(game_state.keys())}")
        print(f"User info: {user_info}")
        
        if not query:
            return format_response({
                "error": "No query provided",
                "status": "error"
            })
        
        # Process the query with the game state
        result = process_query(query, game_state, user_info)
        
        # Return the result
        return format_response(result)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        print(traceback.format_exc())
        return format_response({
            "error": str(e),
            "status": "error"
        })

def format_response(body):
    """Format the response for API Gateway."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps(body)
    } 