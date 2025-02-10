class GameStateManager:
    """Manages real-time game state data (Singleton)."""

    _instance = None

    def __new__(cls):
        """Ensures only one instance of GameStateManager exists."""
        if cls._instance is None:
            cls._instance = super(GameStateManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Use __init__ to define instance attributes.
        Only set default if it hasn't been defined yet, preventing overwriting.
        """
        if not hasattr(self, 'latest_game_state'):
            self.latest_game_state = None

    def update_state(self, new_state: dict):
        """Updates the latest game state."""
        self.latest_game_state = new_state

    def get_state(self):
        """Retrieves the latest stored game state."""
        return self.latest_game_state
