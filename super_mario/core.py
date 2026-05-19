"""核心规则与数据结构 —— 不依赖 Pygame，可独立单测。"""
import json
import math
import os
import random

from super_mario.config import (
    TILE_SIZE, TILE_GROUND,
    CHAR_PLAYER, CHAR_COIN, CHAR_ENEMY_MUSH, CHAR_ENEMY_BIRD,
    CHAR_QUESTION, CHAR_USED_BLOCK, CHAR_FLAG,
    GRAVITY, MAX_FALL_SPEED, PLAYER_SPEED, PLAYER_JUMP_VEL,
    MUSHROOM_SPEED, BIRD_SPEED, BIRD_FLOAT_AMPLITUDE,
    INITIAL_LIVES, COIN_SCORE, STOMP_SCORE, INVINCIBLE_DURATION,
    SAVE_DIR, SAVE_FILE,
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


# ── Level Parsing ─────────────────────────────────────────────────────────────

def parse_level(level_text):
    """将文本关卡字符串列表解析为游戏实体字典。"""
    tiles = []
    coins = []
    enemies = []
    question_blocks = []
    flag = None
    player_spawn = (TILE_SIZE, TILE_SIZE)

    for row, line in enumerate(level_text):
        for col, char in enumerate(line):
            x = col * TILE_SIZE
            y = row * TILE_SIZE

            if char == TILE_GROUND:
                tiles.append(Tile(x, y))
            elif char == CHAR_PLAYER:
                player_spawn = (x, y)
            elif char == CHAR_COIN:
                coins.append(Coin(x, y))
            elif char == CHAR_ENEMY_MUSH:
                enemies.append(Enemy(x, y, 'mush'))
            elif char == CHAR_ENEMY_BIRD:
                enemies.append(Enemy(x, y, 'bird'))
            elif char == CHAR_QUESTION:
                question_blocks.append(QuestionBlock(x, y))
            elif char == CHAR_USED_BLOCK:
                qb = QuestionBlock(x, y)
                qb.triggered = True
                question_blocks.append(qb)
            elif char == CHAR_FLAG:
                flag = Flag(x, y)

    max_cols = max((len(line) for line in level_text), default=0)

    return {
        'tiles': tiles,
        'coins': coins,
        'enemies': enemies,
        'question_blocks': question_blocks,
        'flag': flag,
        'player_spawn': player_spawn,
        'width': max_cols * TILE_SIZE,
        'height': len(level_text) * TILE_SIZE,
    }


# ── Player Physics ────────────────────────────────────────────────────────────

def update_player(player, tiles, question_blocks, dt, move_left, move_right, jump_pressed):
    """更新玩家物理（含碰撞）。返回从下方顶到的 QuestionBlock 列表。

    所有 QuestionBlock（触发/未触发）均为固体。
    纵向碰撞时若 player 上升且碰到 QuestionBlock → 记录到返回值。
    """
    # 合并固体碰撞体: 砖块 + 所有问号砖块
    solids = list(tiles)
    solids.extend(question_blocks)

    # ── 水平移动 ──
    player.vx = 0.0
    if move_left:
        player.vx = -PLAYER_SPEED
        player.facing_right = False
    if move_right:
        player.vx = PLAYER_SPEED
        player.facing_right = True

    player.x += player.vx * dt
    for solid in solids:
        if player.rect.colliderect(solid.rect):
            if player.vx > 0:
                player.x = solid.rect.left - player.width
            elif player.vx < 0:
                player.x = solid.rect.right

    # ── 重力 ──
    player.vy += GRAVITY * dt
    if player.vy > MAX_FALL_SPEED:
        player.vy = MAX_FALL_SPEED

    # ── 跳跃 ──
    if jump_pressed and player.on_ground:
        player.vy = PLAYER_JUMP_VEL
        player.on_ground = False

    # ── 纵向移动 + 检测顶击问号砖块 ──
    hit_blocks = []
    player.y += player.vy * dt
    player.on_ground = False
    for solid in solids:
        if player.rect.colliderect(solid.rect):
            if player.vy > 0:  # 下落 → 落地
                player.y = solid.rect.top - player.height
                player.vy = 0.0
                player.on_ground = True
            elif player.vy < 0:  # 上升 → 顶头
                player.y = solid.rect.bottom
                player.vy = 0.0
                # 记录从下方顶击的问号砖块
                if isinstance(solid, QuestionBlock):
                    hit_blocks.append(solid)

    # ── 无敌计时 ──
    if player.invincible_timer > 0:
        player.invincible_timer -= dt
        if player.invincible_timer < 0:
            player.invincible_timer = 0.0

    # ── 掉出地图 ──
    if player.y > 2000:
        player.alive = False

    return hit_blocks


# ── Enemy Updates ─────────────────────────────────────────────────────────────

def update_enemies(enemies, tiles, dt):
    """更新所有敌人的位置和方向。"""
    tile_rects = [t.rect for t in tiles]

    for enemy in enemies:
        if not enemy.alive:
            continue

        if enemy.enemy_type == 'mush':
            # 重力
            enemy.vy += GRAVITY * dt
            if enemy.vy > MAX_FALL_SPEED:
                enemy.vy = MAX_FALL_SPEED

            # 横向移动
            enemy.x += enemy.vx * dt
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vx > 0:
                        enemy.x = tr.left - enemy.width
                    elif enemy.vx < 0:
                        enemy.x = tr.right
                    enemy.vx = -enemy.vx
                    break

            # 纵向移动 + 落地
            enemy.y += enemy.vy * dt
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vy > 0:
                        enemy.y = tr.top - enemy.height
                        enemy.vy = 0.0
                    elif enemy.vy < 0:
                        enemy.y = tr.bottom
                        enemy.vy = 0.0

            # 边缘检测: 前方没有地面则转向
            edge_x = enemy.x + (enemy.width if enemy.vx > 0 else -1)
            edge_rect = Rect(edge_x, enemy.y + enemy.height + 1, 1, 1)
            on_edge = any(edge_rect.colliderect(tr) for tr in tile_rects)
            if not on_edge:
                enemy.vx = -enemy.vx

        elif enemy.enemy_type == 'bird':
            enemy.float_phase += dt * 3.0
            enemy.x += enemy.vx * dt
            enemy.y += math.sin(enemy.float_phase) * BIRD_FLOAT_AMPLITUDE * dt * 3.0
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vx > 0:
                        enemy.x = tr.left - enemy.width
                    elif enemy.vx < 0:
                        enemy.x = tr.right
                    enemy.vx = -enemy.vx
                    break


# ── Game Rules ────────────────────────────────────────────────────────────────

def handle_coin_collisions(player, coins):
    """玩家与金币碰撞。返回收集数量。"""
    collected = 0
    for coin in coins:
        if not coin.collected and player.rect.colliderect(coin.rect):
            coin.collected = True
            player.score += COIN_SCORE
            player.coins += 1
            collected += 1
    return collected


def handle_enemy_collisions(player, enemies):
    """玩家与敌人碰撞。返回 ('stomp'|'hurt'|None)。"""
    if player.invincible:
        return None

    for enemy in enemies:
        if not enemy.alive:
            continue
        if not player.rect.colliderect(enemy.rect):
            continue

        # 踩踏: 玩家下落且脚底靠近敌人顶部
        # 阈值取最大一帧下落距离的 1.5 倍 (MAX_FALL_SPEED * 0.05 * 1.5 ≈ 72)
        stomp_threshold = MAX_FALL_SPEED * 0.05 * 1.5
        if player.vy > 0 and (player.rect.bottom - enemy.rect.top) < stomp_threshold:
            enemy.alive = False
            player.score += STOMP_SCORE
            player.vy = PLAYER_JUMP_VEL * 0.6
            return 'stomp'
        else:
            player.lives -= 1
            player.invincible_timer = INVINCIBLE_DURATION
            return 'hurt'

    return None


def handle_top_collisions(player, hit_blocks):
    """处理 update_player 检测到的顶击问号砖块, 发放奖励。

    Args:
        player: 玩家实例 (用于增加分数/生命)
        hit_blocks: update_player() 返回的 QuestionBlock 列表

    Returns:
        list of ('coin'|'life')
    """
    results = []
    for qb in hit_blocks:
        if qb.triggered:
            continue
        qb.triggered = True
        qb.bounce_offset = 6.0
        if random.random() < 0.5:
            player.score += COIN_SCORE
            player.coins += 1
            results.append('coin')
        else:
            player.lives += 1
            results.append('life')
    return results


def handle_flag_collision(player, flag):
    """检查玩家是否到达终点旗。"""
    if flag is None:
        return False
    return player.rect.colliderect(flag.rect)


# ── Save System ───────────────────────────────────────────────────────────────

def _default_save():
    """返回全新默认存档 (每次调用创建新对象, 避免嵌套 dict 共享引用)。"""
    return {
        'unlocked_level': 1,
        'best_scores': {'level_1': 0, 'level_2': 0, 'level_3': 0},
    }


def load_save():
    """读取最高分存档, 文件不存在时返回默认值。"""
    if not os.path.exists(SAVE_FILE):
        return _default_save()
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = _default_save()
        result.update(data)
        return result
    except (json.JSONDecodeError, IOError):
        return _default_save()


def write_save(data):
    """写入存档, 失败返回 False。"""
    os.makedirs(SAVE_DIR, exist_ok=True)
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except IOError:
        return False
