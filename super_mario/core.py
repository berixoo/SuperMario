"""核心规则与数据结构 —— 不依赖 Pygame，可独立单测。"""
from super_mario.config import (
    TILE_SIZE, TILE_GROUND, TILE_EMPTY,
    CHAR_PLAYER, CHAR_COIN, CHAR_ENEMY_MUSH, CHAR_ENEMY_BIRD,
    CHAR_QUESTION, CHAR_USED_BLOCK, CHAR_FLAG,
    GRAVITY, MAX_FALL_SPEED, PLAYER_SPEED, PLAYER_JUMP_VEL,
    MUSHROOM_SPEED, BIRD_SPEED, BIRD_FLOAT_AMPLITUDE,
    INITIAL_LIVES, COIN_SCORE, STOMP_SCORE, INVINCIBLE_DURATION,
)


class Rect:
    """纯 Python 矩形，替代 pygame.Rect 用于碰撞检测。"""
    def __init__(self, x, y, width, height):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height

    @property
    def left(self): return self.x

    @property
    def right(self): return self.x + self.width

    @property
    def top(self): return self.y

    @property
    def bottom(self): return self.y + self.height

    def colliderect(self, other):
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )


class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.on_ground = False
        self.facing_right = True
        self.lives = INITIAL_LIVES
        self.score = 0
        self.coins = 0
        self.invincible_timer = 0.0
        self.alive = True

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)

    @property
    def invincible(self):
        return self.invincible_timer > 0


class Enemy:
    def __init__(self, x, y, enemy_type='mush'):
        self.x = float(x)
        self.y = float(y)
        self.vx = -MUSHROOM_SPEED if enemy_type == 'mush' else -BIRD_SPEED
        self.vy = 0.0
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.enemy_type = enemy_type  # 'mush' or 'bird'
        self.alive = True
        self.float_phase = 0.0

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.collected = False

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


class QuestionBlock:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.triggered = False
        self.bounce_offset = 0.0

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


class Tile:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


class Flag:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE * 2

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)
