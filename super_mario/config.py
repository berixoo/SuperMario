"""全局配置常量。"""
import os

# ── Window ──────────────────────────────────
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TILE_SIZE = 32

# ── Physics (per-second, used with dt) ──────
PLAYER_SPEED = 300          # px/s
PLAYER_JUMP_VEL = -720      # px/s (negative = upward)
GRAVITY = 1800              # px/s²
MAX_FALL_SPEED = 960        # px/s

# ── Enemy ───────────────────────────────────
MUSHROOM_SPEED = 90         # px/s
BIRD_SPEED = 120            # px/s
BIRD_FLOAT_AMPLITUDE = 24   # px

# ── Game rules ──────────────────────────────
INITIAL_LIVES = 3
COIN_SCORE = 100
STOMP_SCORE = 300
INVINCIBLE_DURATION = 1.5   # seconds
LEVEL_TIMES = {1: 120, 2: 100, 3: 90}

# ── Tile chars ──────────────────────────────
TILE_GROUND = '#'
TILE_EMPTY = '.'
CHAR_PLAYER = 'P'
CHAR_COIN = 'C'
CHAR_ENEMY_MUSH = 'E'
CHAR_ENEMY_BIRD = 'B'
CHAR_QUESTION = 'Q'
CHAR_USED_BLOCK = 'U'
CHAR_FLAG = 'F'

# ── Colors ──────────────────────────────────
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
YELLOW = (255, 255, 0)

# ── Paths ───────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
SAVE_DIR = os.path.join(_BASE_DIR, "save")
SAVE_FILE = os.path.join(SAVE_DIR, "highscore.json")
