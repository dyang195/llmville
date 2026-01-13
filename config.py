"""Game configuration constants."""

# Window settings
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
FPS = 60
TITLE = "Social Simulation"

# Grid settings
GRID_WIDTH = 50
GRID_HEIGHT = 50
TILE_SIZE = 32

# Camera settings
CAMERA_SPEED = 500  # Pixels per second when scrolling

# Entity settings
DEFAULT_HEALTH = 100.0
HEALTH_REGEN_RATE = 0.1  # Per game minute
DEFAULT_MONEY = 50.0
MOVEMENT_SPEED = 2.0  # Tiles per second
INVENTORY_CAPACITY = 20

# Time settings
TIME_SCALE = 60.0  # 1 real second = 1 game minute
MINUTES_PER_DAY = 1440  # 24 hours * 60 minutes

# Interaction settings
INTERACTION_COOLDOWN = 30.0  # Game minutes between interactions with same entity
CONVERSATION_CHANCE = 0.7  # Base chance to start conversation when adjacent

# AI settings
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_CONVERSATION_TURNS = 6  # Per participant (so 6 exchanges total = 12 messages max)
API_REQUESTS_PER_MINUTE = 50
API_TOKENS_PER_MINUTE = 40000

# Colors (RGB)
COLORS = {
    "background": (34, 34, 34),
    "grass": (76, 153, 76),
    "road": (139, 119, 101),
    "water": (64, 164, 223),
    "building": (139, 90, 43),
    "grid_line": (50, 50, 50),
    "entity": (255, 200, 100),
    "entity_talking": (255, 100, 100),
    "ui_background": (45, 45, 45),
    "ui_border": (100, 100, 100),
    "text": (255, 255, 255),
    "text_dim": (180, 180, 180),
    "highlight": (255, 215, 0),
}

# Personality traits (and their ranges)
PERSONALITY_TRAITS = [
    "friendliness",
    "greed",
    "honesty",
    "bravery",
    "curiosity",
    "patience",
]

# Speech styles
SPEECH_STYLES = ["formal", "casual", "gruff", "flowery", "terse", "cheerful"]

# Roles
ROLES = ["shopkeeper", "farmer", "guard", "villager", "blacksmith", "innkeeper"]
