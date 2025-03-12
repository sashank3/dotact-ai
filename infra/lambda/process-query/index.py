import json
import os
import logging
import traceback
import datetime

# Configure logging first - this is used throughout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize boto3 client only when needed
def get_secrets_manager_client():
    import boto3
    return boto3.client('secretsmanager')

def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager"""
    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            import base64
            return json.loads(base64.b64decode(response['SecretBinary']))
    except Exception as e:
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
    Based on whether game state data is valid or not, use different prompts.
    """
    # Check if game state has valid data
    has_valid_game_state = not game_state_text.startswith("=== DOTA 2 GAME STATE ===\nNo valid game state data available.")
    
    if has_valid_game_state:
        system_content = (
            "You are an expert Dota 2 assistant that provides highly relevant in-game advice. "
            "Format your response with two main sections:\n\n"
            "RECOMMENDED ITEMS\n"
            "• List 2-5 recommended items in order of priority (highest priority first)\n"
            "• Include a priority rating for each item (Critical, High, Medium, or Low)\n\n"
            "GAME STRATEGIES\n"
            "• List 2-5 strategies based on the current game state in order of priority\n"
            "• Include a priority rating for each strategy (Critical, High, Medium, or Low)\n\n"
            "Keep explanations clear and concise, prioritize high-impact recommendations, "
            "and ensure advice is immediately actionable based on the current game state.\n\n"
            "If the query is NOT related to Dota 2, respond only with: \"I'm a Dota 2 assistant and can only "
            "provide information related to Dota 2. Please ask me about heroes, items, strategies, or other "
            "game-related topics.\""
        )
    else:
        system_content = (
            "You are an expert Dota 2 assistant providing general game advice. "
            "Since no specific game data is available, offer generic Dota 2 guidance.\n\n"
            "Format your response with two main sections:\n\n"
            "RECOMMENDED ITEMS\n"
            "• List 2-5 generally useful items in order of priority (highest priority first)\n"
            "• Include a priority rating for each item (Critical, High, Medium, or Low)\n\n"
            "GAME STRATEGIES\n"
            "• List 2-5 general Dota 2 strategies in order of priority\n"
            "• Include a priority rating for each strategy (Critical, High, Medium, or Low)\n\n"
            "Keep explanations clear and concise. Do not use explicit markdown formatting.\n\n"
            "If the query is NOT related to Dota 2, respond only with: \"I'm a Dota 2 assistant and can only "
            "provide information related to Dota 2. Please ask me about heroes, items, strategies, or other "
            "game-related topics.\""
        )
    
    return [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": (
                f"Game Context:\n{game_state_text}\n\n"
                f"Player Query: {user_query}\n"
            )
        }
    ]

def get_llm_response(query, game_state, user_info, api_key, chat_context=None):
    """
    Get a response from the LLM model using the Fireworks API.
    
    Args:
        query: The user's query text
        game_state: The current game state
        user_info: User information
        api_key: The Fireworks API key
        chat_context: Previous conversation history in OpenAI format (optional)
        
    Returns:
        The LLM's response as a string
    """
    try:
        # Convert game state to readable text format
        game_state_text, hero_name = convert_game_state_to_text(game_state)
        
        # If we have chat context, use it to maintain conversation history
        if chat_context and isinstance(chat_context, list) and len(chat_context) > 0:
            logger.info(f"Using provided chat context with {len(chat_context)} messages")
            
            # Find system message if it exists
            has_system_message = any(msg.get('role') == 'system' for msg in chat_context)
            
            if not has_system_message:
                # No system message found, use build_prompt to get the proper system message
                # and then combine with existing chat context
                prompt_messages = build_prompt(query, game_state_text)
                system_message = next((msg for msg in prompt_messages if msg.get('role') == 'system'), None)
                
                if system_message:
                    # Add system message at the beginning
                    chat_context = [system_message] + [
                        msg for msg in chat_context if msg.get('role') != 'system'
                    ]
            
            # Create a new user message with the current query and game state
            # This ensures every interaction has the latest game state
            new_user_message = {
                "role": "user", 
                "content": f"Game Context:\n{game_state_text}\n\nPlayer Query: {query}"
            }
            
            # Add the new user message to the chat context
            messages = chat_context + [new_user_message]
            
        else:
            # No chat context provided, use the default prompt
            logger.info("No chat context provided, using default prompt")
            messages = build_prompt(query, game_state_text)
        
        # Initialize the OpenAI client with Fireworks endpoint - only import OpenAI when needed
        from openai import OpenAI
        client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=api_key,
            timeout=30
        )
        
        # Call the LLM API
        response = client.chat.completions.create(
            model="accounts/fireworks/models/deepseek-r1",
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
            timeout=30  # Set timeout to prevent Lambda timeout
        )
        
        # Extract the completion text
        completion = response.choices[0].message.content
        return completion
        
    except Exception as e:
        logger.error(f"Error calling LLM service: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request. Please try again."

def get_api_key_from_secrets():
    """
    Get the LLM API key from AWS Secrets Manager.
    
    Returns:
        str: The API key
    """
    try:
        # Get the secret - use environment variable or default to 'LLMCredentials'
        secret_name = os.environ.get('SECRETS_NAME', 'LLMCredentials')
        logger.info(f"Looking for secret: {secret_name}")
        
        secrets_client = get_secrets_manager_client()
        response = secrets_client.get_secret_value(
            SecretId=secret_name
        )
        
        # Parse the secret
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            
            # If there's only one key in the secret, use that
            if len(secret) == 1:
                only_key = list(secret.values())[0]
                logger.info("Using the only available key in the secret")
                return only_key
            else:
                logger.warning("API key not found in Secrets Manager")
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting API key from Secrets Manager: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def handler(event, context):
    """
    Process a user query using the game state and user information.
    
    This function is the entry point for the Lambda.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract authorization information
        auth_header = event.get('headers', {}).get('Authorization')
        auth_source = event.get('headers', {}).get('X-Auth-Source')
        user_id = 'anonymous'
        
        # Validate authentication if provided
        if auth_header and auth_header.startswith('Bearer '):
            # Extract user ID from authorization context
            user_id = event.get('requestContext', {}).get('authorizer', {}).get('principalId', 'authenticated-user')
            logger.info(f"Using authenticated user: {user_id}")
        else:
            logger.warning("No valid authorization header found")
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        query = body.get('query')
        game_state = body.get('game_state', {})
        user_info = body.get('user_info', {})
        chat_context = body.get('chat_context', [])  # Get chat context from request
        
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Query is required'})
            }
        
        # Get API credentials from Secrets Manager
        api_key = get_api_key_from_secrets()
        
        if not api_key:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to retrieve API credentials'})
            }
        
        # Process the query using Nebius LLM
        completion = get_llm_response(query, game_state, user_info, api_key, chat_context)
        
        # Return the result
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'answer': completion,
                'user_id': user_id,
                'timestamp': datetime.datetime.now().isoformat()
            })
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }