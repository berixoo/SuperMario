# 超级马里奥风格小游戏 — 完整版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零实现完整版超级马里奥风格横版平台跳跃游戏，包含 3 关卡、菜单系统、问号砖块、倒计时、最高分存档。

**Architecture:** 按文档推荐的 6 模块结构。`core.py` 为纯 Python 逻辑（不依赖 Pygame），可单测；`sprites.py` 封装 Pygame 绘制；`game.py` 管理状态机和主循环。状态分发使用显式 if-elif。

**Tech Stack:** Python 3.10+, Pygame 2.x, JSON 存档, pytest (core.py 单测)

---

### Task 1: 项目脚手架

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `super_mario/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
pygame>=2.0
```

- [ ] **Step 2: 创建 .gitignore**

```gitignore
__pycache__/
*.pyc
*.pyo
.claude/
save/
*.egg-info/
dist/
build/
```

- [ ] **Step 3: 创建 super_mario/__init__.py（空文件）**

- [ ] **Step 4: 初始化 git 仓库并首次提交**

```bash
cd "D:\Desktop\workspace\SuperMario"
git init
git add requirements.txt .gitignore super_mario/__init__.py
git commit -m "chore: init project scaffold"
```

---

### Task 2: config.py

**Files:**
- Create: `super_mario/config.py`

- [ ] **Step 1: 写入配置常量**

```python
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
```

- [ ] **Step 2: 验证可导入**

```bash
cd "D:\Desktop\workspace\SuperMario" && python -c "from super_mario.config import SCREEN_WIDTH; print(SCREEN_WIDTH)"
```
Expected: `800`

- [ ] **Step 3: 提交**

```bash
git add super_mario/config.py
git commit -m "feat: add config module"
```

---

### Task 3: core.py — 数据结构与 Rect

**Files:**
- Create: `super_mario/core.py`

- [ ] **Step 1: 写入实体类和 Rect**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/core.py
git commit -m "feat: add core data structures and Rect"
```

---

### Task 4: core.py — 关卡解析 + 物理 + 游戏规则 + 存档

**Files:**
- Modify: `super_mario/core.py` (追加函数, 不动已有类)

- [ ] **Step 1: 追加关卡解析函数**

```python
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
```

- [ ] **Step 2: 追加物理更新函数**

关键设计：
- **所有** QuestionBlock（含已触发）都作为固体砖块。
- 纵向碰撞发生时，如果 `player.vy < 0` 且碰撞对象是 QuestionBlock，则将该块加入返回列表。
- 触发状态 (`triggered`) 只控制是否给奖励和显示哪个图片，不影响碰撞。

```python
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
```

- [ ] **Step 3: 追加敌人更新函数**

```python
import math


def update_enemies(enemies, tiles, dt):
    """更新所有敌人的位置和方向。"""
    tile_rects = [t.rect for t in tiles]

    for enemy in enemies:
        if not enemy.alive:
            continue

        if enemy.enemy_type == 'mush':
            enemy.x += enemy.vx * dt
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vx > 0:
                        enemy.x = tr.left - enemy.width
                    elif enemy.vx < 0:
                        enemy.x = tr.right
                    enemy.vx = -enemy.vx
                    break
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
```

- [ ] **Step 4: 追加游戏规则处理函数**

`handle_top_collisions` 接受 `update_player` 返回的 `hit_blocks` 列表，只负责发放奖励，不再自行判断碰撞。

```python
import random


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
        if player.vy > 0 and (player.rect.bottom - enemy.rect.top) < 20:
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
```

- [ ] **Step 5: 追加存档读写函数**

```python
import json
import os
from super_mario.config import SAVE_DIR, SAVE_FILE


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
```

- [ ] **Step 6: 验证所有函数可导入**

```bash
cd "D:\Desktop\workspace\SuperMario" && python -c "
from super_mario.core import (
    Rect, Player, Enemy, Coin, QuestionBlock, Tile, Flag,
    parse_level, update_player, update_enemies,
    handle_coin_collisions, handle_enemy_collisions,
    handle_top_collisions, handle_flag_collision,
    load_save, write_save,
)
print('All imports OK')
"
```
Expected: `All imports OK`

- [ ] **Step 7: 提交**

```bash
git add super_mario/core.py
git commit -m "feat: add level parser, physics, game rules, and save system"
```

---

### Task 5: core.py 单元测试

**Files:**
- Create: `tests/__init__.py` (空文件)
- Create: `tests/test_core.py`

- [ ] **Step 1: 安装 pytest**

```bash
pip install pytest
```

- [ ] **Step 2: 写入 core.py 单元测试**

```python
"""core.py 纯逻辑单元测试。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from super_mario.config import TILE_SIZE, INITIAL_LIVES, COIN_SCORE, STOMP_SCORE
from super_mario.core import (
    Rect, Player, Enemy, Coin, QuestionBlock, Tile, Flag,
    parse_level, update_player, update_enemies,
    handle_coin_collisions, handle_enemy_collisions,
    handle_top_collisions, handle_flag_collision,
    load_save, write_save,
)


# ═══════════════════════════════════════════════
# Rect
# ═══════════════════════════════════════════════

class TestRect:
    def test_collision_true(self):
        a = Rect(0, 0, 32, 32)
        b = Rect(16, 16, 32, 32)
        assert a.colliderect(b)

    def test_collision_false(self):
        a = Rect(0, 0, 32, 32)
        b = Rect(64, 0, 32, 32)
        assert not a.colliderect(b)

    def test_collision_adjacent_is_false(self):
        """紧挨不重叠不算碰撞。"""
        a = Rect(0, 0, 32, 32)
        b = Rect(32, 0, 32, 32)
        assert not a.colliderect(b)

    def test_properties(self):
        r = Rect(10, 20, 30, 40)
        assert r.left == 10
        assert r.right == 40
        assert r.top == 20
        assert r.bottom == 60


# ═══════════════════════════════════════════════
# parse_level
# ═══════════════════════════════════════════════

SIMPLE_MAP = [
    "P...C..F",
    "####.###",
]


class TestParseLevel:
    def test_player_spawn(self):
        result = parse_level(SIMPLE_MAP)
        assert result['player_spawn'] == (0, 0)

    def test_tiles(self):
        result = parse_level(SIMPLE_MAP)
        assert len(result['tiles']) == 8

    def test_coins(self):
        result = parse_level(SIMPLE_MAP)
        assert len(result['coins']) == 1

    def test_flag(self):
        result = parse_level(SIMPLE_MAP)
        assert result['flag'] is not None
        assert result['flag'].x == 7 * TILE_SIZE

    def test_width_height(self):
        result = parse_level(SIMPLE_MAP)
        assert result['width'] == 8 * TILE_SIZE
        assert result['height'] == 2 * TILE_SIZE

    def test_enemy_mush(self):
        result = parse_level(["P.E..F", "#####"])
        assert len(result['enemies']) == 1
        assert result['enemies'][0].enemy_type == 'mush'

    def test_enemy_bird(self):
        result = parse_level(["P.B..F", "#####"])
        assert len(result['enemies']) == 1
        assert result['enemies'][0].enemy_type == 'bird'

    def test_question_block(self):
        result = parse_level(["P.Q..F", "#####"])
        assert len(result['question_blocks']) == 1
        assert not result['question_blocks'][0].triggered

    def test_used_block(self):
        result = parse_level(["P.U..F", "#####"])
        assert len(result['question_blocks']) == 1
        assert result['question_blocks'][0].triggered


# ═══════════════════════════════════════════════
# Player physics
# ═══════════════════════════════════════════════

def _make_ground(cols=10):
    return [Tile(c * TILE_SIZE, TILE_SIZE * 3) for c in range(cols)]


class TestPlayerPhysics:
    def test_gravity_pulls_down(self):
        player = Player(TILE_SIZE, 0)
        tiles = _make_ground()
        update_player(player, tiles, [], 0.1, False, False, False)
        assert player.vy > 0

    def test_lands_on_ground(self):
        player = Player(TILE_SIZE, TILE_SIZE * 3 - TILE_SIZE)
        tiles = _make_ground()
        for _ in range(30):
            update_player(player, tiles, [], 1.0 / 60, False, False, False)
        assert player.on_ground
        # 玩家脚底 = 地面 tile 的顶部
        assert abs(player.rect.bottom - TILE_SIZE * 3) < 1.0

    def test_jump_sets_velocity(self):
        player = Player(TILE_SIZE, TILE_SIZE * 3 - TILE_SIZE)
        tiles = _make_ground()
        for _ in range(30):
            update_player(player, tiles, [], 1.0 / 60, False, False, False)
        assert player.on_ground
        update_player(player, tiles, [], 1.0 / 60, False, False, True)
        assert player.vy < 0

    def test_wall_stops_horizontal(self):
        player = Player(0, TILE_SIZE * 3 - TILE_SIZE)
        tiles = _make_ground()
        tiles.append(Tile(TILE_SIZE * 2, TILE_SIZE * 3 - TILE_SIZE))
        for _ in range(60):
            update_player(player, tiles, [], 1.0 / 60, True, False, False)
        assert player.rect.right <= TILE_SIZE * 2 + 1

    def test_falls_off_bottom_dies(self):
        player = Player(0, 0)
        for _ in range(300):
            update_player(player, [], [], 1.0 / 60, False, False, False)
        assert not player.alive

    def test_triggered_block_is_still_solid(self):
        """已触发的问号砖块仍是固体：玩家会站在上面。"""
        qb = QuestionBlock(TILE_SIZE, 0)
        qb.triggered = True
        # 玩家在 QB 上方稍高，重力会拉下来站到 QB 上
        player = Player(TILE_SIZE + 2, -10)
        for _ in range(60):
            update_player(player, [], [qb], 1.0 / 60, False, False, False)
        assert player.on_ground
        assert abs(player.rect.bottom - qb.rect.top) < 1.0

    def test_hit_block_from_below_returns_block(self):
        """从下方顶到问号砖块时, update_player 返回该砖块。"""
        qb = QuestionBlock(TILE_SIZE, TILE_SIZE * 2)
        player = Player(TILE_SIZE, TILE_SIZE * 2 + TILE_SIZE)
        # 地面必须在玩家正下方 (同一 x 列)，否则不会发生碰撞落地
        tiles = [Tile(TILE_SIZE, TILE_SIZE * 4)]
        # 先落地 (重力拉下来 → 站在 tile 上 → on_ground = True)
        for _ in range(90):
            update_player(player, tiles, [], 1.0 / 60, False, False, False)
        assert player.on_ground, "player should land before jump"
        # 跳跃顶砖块
        hit = update_player(player, tiles, [qb], 1.0 / 60, False, False, True)
        for _ in range(60):
            if hit:
                break
            hit = update_player(player, tiles, [qb], 1.0 / 60, False, False, False)
        assert len(hit) > 0
        assert isinstance(hit[0], QuestionBlock)


# ═══════════════════════════════════════════════
# Game rules
# ═══════════════════════════════════════════════

class TestGameRules:
    def test_collect_coin(self):
        player = Player(16, 16)
        coin = Coin(20, 20)
        n = handle_coin_collisions(player, [coin])
        assert n == 1
        assert coin.collected
        assert player.score == COIN_SCORE
        assert player.coins == 1

    def test_coin_already_collected(self):
        player = Player(16, 16)
        coin = Coin(20, 20)
        coin.collected = True
        n = handle_coin_collisions(player, [coin])
        assert n == 0
        assert player.score == 0

    def test_coin_no_collision(self):
        player = Player(0, 0)
        coin = Coin(200, 200)
        n = handle_coin_collisions(player, [coin])
        assert n == 0

    def test_stomp_enemy(self):
        player = Player(0, 30)
        player.vy = 5.0
        enemy = Enemy(0, 50)
        result = handle_enemy_collisions(player, [enemy])
        assert result == 'stomp'
        assert not enemy.alive
        assert player.score == STOMP_SCORE

    def test_hurt_by_enemy(self):
        player = Player(0, 50)
        enemy = Enemy(0, 50)
        result = handle_enemy_collisions(player, [enemy])
        assert result == 'hurt'
        assert enemy.alive
        assert player.lives == INITIAL_LIVES - 1
        assert player.invincible

    def test_invincible_ignores_enemy(self):
        player = Player(0, 50)
        player.invincible_timer = 1.0
        enemy = Enemy(0, 50)
        result = handle_enemy_collisions(player, [enemy])
        assert result is None

    def test_top_collision_triggers_block(self):
        """handle_top_collisions 处理 update_player 返回的 hit_blocks。"""
        qb = QuestionBlock(0, 0)
        qb.triggered = False
        player = Player(0, 0)
        results = handle_top_collisions(player, [qb])
        assert qb.triggered
        assert qb.bounce_offset == 6.0
        assert len(results) == 1
        assert results[0] in ('coin', 'life')

    def test_top_collision_already_triggered_gives_nothing(self):
        qb = QuestionBlock(0, 0)
        qb.triggered = True
        player = Player(0, 0)
        results = handle_top_collisions(player, [qb])
        assert len(results) == 0

    def test_flag_collision(self):
        player = Player(0, 0)
        flag = Flag(16, 16)
        assert handle_flag_collision(player, flag)

    def test_flag_no_collision(self):
        player = Player(0, 0)
        flag = Flag(200, 200)
        assert not handle_flag_collision(player, flag)

    def test_flag_none(self):
        assert not handle_flag_collision(Player(0, 0), None)


# ═══════════════════════════════════════════════
# Save system
# ═══════════════════════════════════════════════

class TestSave:
    def test_load_default(self):
        data = load_save()
        assert data['unlocked_level'] == 1
        assert 'level_1' in data['best_scores']

    def test_write_and_load(self):
        data = {'unlocked_level': 2,
                'best_scores': {'level_1': 500, 'level_2': 0, 'level_3': 0}}
        ok = write_save(data)
        assert ok
        loaded = load_save()
        assert loaded['unlocked_level'] == 2
        assert loaded['best_scores']['level_1'] == 500
        # 还原默认
        write_save({'unlocked_level': 1,
                    'best_scores': {'level_1': 0, 'level_2': 0, 'level_3': 0}})
```

- [ ] **Step 3: 运行测试并确认通过**

```bash
cd "D:\Desktop\workspace\SuperMario" && python -m pytest tests/test_core.py -v
```
Expected: 全部 PASS (22 tests)

- [ ] **Step 4: 提交**

```bash
git add tests/ super_mario/core.py
git commit -m "test: add core.py unit tests (22 cases)"
```

---

### Task 6: level_data.py — 3个关卡地图

**Files:**
- Create: `super_mario/level_data.py`

- [ ] **Step 1: 写入关卡数据**

```python
"""关卡文本地图数据。

字符含义: #=地面 P=玩家 C=金币 E=蘑菇敌人 B=飞行敌人 Q=问号 U=已触发问号 F=终点旗 .=空白
"""

LEVEL_1 = [
    "................................................................................................F",
    "...........C..........C...................C...........C.........................................###",
    "P.........#####......#####...............#####.......#####......C..........C..........C.............",
    ".......C............................C..........................####.......####.......####..........",
    "......####..........E.............####...........E................................................",
    "........................................C.........................................................",
    "...........C..........C...................C...........C...........................................",
    "..........####......####...............####.......####............................................",
    "................E...............................E................E.........................E.......",
    "..................................................................................................",
    "...........####..............####..............####..............####...............####...........",
    "################################################################################################",
]
"""第 1 关「绿色草原」: 120s, ~96×12, 简单跳跃 + 蘑菇敌人"""

LEVEL_2 = [
    "..........................................................................................................F",
    "...........C...................C..........C...................C...........C.............................###",
    "P.........#####...............#####......#####...............#####.......#####..........C.................",
    ".......C.................C............................C............................####....C..............",
    "......####........E......####..E.....................####..........E.............####...####.............",
    "...............#####...............#####...............................................................",
    ".....B...................B..................B...................B.................B.....................",
    "....####......E........####......E........####......E........####......E........####......E..............",
    "........................................C...........C...........................................C.......",
    "..........C...................C..........C...........C..........C...................C.........C.........",
    "......####....C..........####.................C.........C............####...................####........",
    "................E....................E............................E....................E.................",
    "########################################################################################################",
]
"""第 2 关「地下洞穴」: 100s, ~104×13, 金币 + 蘑菇 + 飞行敌人"""

LEVEL_3 = [
    "..........................................................................................................................F",
    "...........C..........C...........C..........C...........C..........C...........C..........C...........C.................###",
    "P.........#####......#####.......#####......#####.......#####......#####.......#####......#####.......#####.......C..........",
    ".......C........C...........C.........C..........C...........C.........C..........C...........C.........C.....####...........",
    "......####..Q...####...Q...####...Q...####...Q..####...Q...####...Q..####...Q...####...Q...####...Q...####...####..Q.........",
    ".....B..........B...........B..........B...........B..........B...........B..........B...........B..........B...............",
    "....####..E....####..E....####..E....####..E....####..E....####..E....####..E....####..E....####..E....####..E....####..E....",
    "...........C.........C..........C...........C.........C..........C...........C.........C..........C............C..........C..",
    "......####......####......####......####......####......####......####......####......####......####......####......####.....",
    "...............E...................E...................E...................E...................E...................E.........",
    "........####..............####..............####..............####..............####..............####..............####......",
    "...C........C........C.........C........C.........C........C.........C........C.........C........C.........C........C......",
    "..####....####....####.....####....####.....####....####.....####....####.....####....####.....####....####.....####....####.",
    ".....E..........E..........E..........E..........E..........E..........E..........E..........E..........E..........E.........",
    "##############################################################################################################################",
]
"""第 3 关「天空城堡」: 90s, ~122×15, 金币 + 蘑菇 + 飞行 + 问号"""

LEVELS = {
    1: {'name': '绿色草原', 'time': 120, 'map': LEVEL_1},
    2: {'name': '地下洞穴', 'time': 100, 'map': LEVEL_2},
    3: {'name': '天空城堡', 'time': 90, 'map': LEVEL_3},
}
```

- [ ] **Step 2: 验证可导入和解析**

```bash
cd "D:\Desktop\workspace\SuperMario" && python -c "from super_mario.level_data import LEVELS; from super_mario.core import parse_level; r=parse_level(LEVELS[1]['map']); print(f'level1: {r[\"width\"]}x{r[\"height\"]}, tiles={len(r[\"tiles\"])}, coins={len(r[\"coins\"])}, enemies={len(r[\"enemies\"])}, flag={r[\"flag\"] is not None}')"
```
Expected: 打印关卡 1 的尺寸和实体数量

- [ ] **Step 3: 提交**

```bash
git add super_mario/level_data.py
git commit -m "feat: add 3 level maps"
```

---

### Task 7: sprites.py — 素材加载与精灵绘制

**Files:**
- Create: `super_mario/sprites.py`

- [ ] **Step 1: 写入精灵模块**

背景图与精灵图分离加载：背景保持原始尺寸（`draw_background` 时缩放），精灵缩放到 TILE_SIZE。

```python
"""精灵显示模块 —— 封装 Pygame 图片加载与绘制。"""
import pygame
from super_mario.config import IMAGES_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

_sprites = {}       # 精灵图: 已缩放到 TILE_SIZE
_backgrounds = {}   # 背景图: 原始尺寸


def _load_sprite(name):
    if name not in _sprites:
        path = f"{IMAGES_DIR}/{name}"
        img = pygame.image.load(path).convert_alpha()
        if name == 'goal_flag.png':
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE * 2))
        else:
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        _sprites[name] = img
    return _sprites[name]


def _load_background(name):
    if name not in _backgrounds:
        path = f"{IMAGES_DIR}/{name}"
        _backgrounds[name] = pygame.image.load(path).convert()
    return _backgrounds[name]


def load_all_assets():
    for name in [
        'player_right.png', 'player_left.png',
        'tile_ground.png', 'coin.png',
        'enemy_mush.png', 'enemy_bird.png',
        'question_block.png', 'used_block.png',
        'life_mushroom.png', 'goal_flag.png',
    ]:
        _load_sprite(name)
    for name in ['background_day.png', 'background_cave.png', 'background_sky_castle.png']:
        _load_background(name)


def draw_background(screen, level_num):
    bg_map = {1: 'background_day.png', 2: 'background_cave.png', 3: 'background_sky_castle.png'}
    bg = _load_background(bg_map.get(level_num, 'background_day.png'))
    bg = pygame.transform.scale(bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(bg, (0, 0))


def draw_tiles(screen, tiles, camera_x):
    img = _load_sprite('tile_ground.png')
    for tile in tiles:
        screen.blit(img, (tile.x - camera_x, tile.y))


def draw_coins(screen, coins, camera_x):
    img = _load_sprite('coin.png')
    for coin in coins:
        if not coin.collected:
            screen.blit(img, (coin.x - camera_x, coin.y))


def draw_enemies(screen, enemies, camera_x):
    mush_img = _load_sprite('enemy_mush.png')
    bird_img = _load_sprite('enemy_bird.png')
    for enemy in enemies:
        if not enemy.alive:
            continue
        img = mush_img if enemy.enemy_type == 'mush' else bird_img
        screen.blit(img, (enemy.x - camera_x, enemy.y))


def draw_question_blocks(screen, question_blocks, camera_x):
    active_img = _load_sprite('question_block.png')
    used_img = _load_sprite('used_block.png')
    for qb in question_blocks:
        img = used_img if qb.triggered else active_img
        screen.blit(img, (qb.x - camera_x, qb.y - qb.bounce_offset))


def draw_player(screen, player, camera_x):
    if player.invincible and int(player.invincible_timer * 10) % 2 == 0:
        return
    name = 'player_right.png' if player.facing_right else 'player_left.png'
    screen.blit(_load_sprite(name), (player.x - camera_x, player.y))


def draw_flag(screen, flag, camera_x):
    if flag is None:
        return
    screen.blit(_load_sprite('goal_flag.png'), (flag.x - camera_x, flag.y))


def draw_hud(screen, player, level_time_remaining, font):
    score_text = font.render(f"Score: {player.score}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    coin_text = font.render(f"Coins: {player.coins}", True, (255, 255, 0))
    screen.blit(coin_text, (10, 40))
    mins = int(max(0, level_time_remaining) // 60)
    secs = int(max(0, level_time_remaining) % 60)
    time_text = font.render(f"Time: {mins:02d}:{secs:02d}", True, (255, 255, 255))
    screen.blit(time_text, (SCREEN_WIDTH // 2 - 50, 10))
    lives_text = font.render(f"Lives: {player.lives}", True, (255, 50, 50))
    screen.blit(lives_text, (SCREEN_WIDTH - 120, 10))
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/sprites.py
git commit -m "feat: add sprite loading and drawing module"
```

---

### Task 8: game.py — 窗口、状态机、主循环骨架 + 中文字体

**Files:**
- Create: `super_mario/game.py`

- [ ] **Step 1: 写入 game.py 完整骨架**

状态分发使用显式 if-elif。字体创建优先使用系统中文无衬线字体。

```python
"""游戏主控制模块 —— 状态机、主循环、输入、音效调度。"""
import sys
import pygame
from super_mario.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TILE_SIZE, AUDIO_DIR,
    INITIAL_LIVES,
)
from super_mario.level_data import LEVELS
from super_mario.core import (
    Player, parse_level, update_player, update_enemies,
    handle_coin_collisions, handle_enemy_collisions,
    handle_top_collisions, handle_flag_collision,
    load_save, write_save,
)
from super_mario import sprites


def _make_font(size):
    """创建可渲染中文的字体。用 match_font 验证字体存在再使用。"""
    for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial"]:
        matched = pygame.font.match_font(name)
        if matched:
            return pygame.font.Font(matched, size)
    return pygame.font.Font(None, size)


class Game:
    STATE_TITLE = 'title'
    STATE_LEVEL_SELECT = 'level_select'
    STATE_PLAYING = 'playing'
    STATE_PAUSED = 'paused'
    STATE_WIN = 'win'
    STATE_GAME_OVER = 'game_over'

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Mario Adventure")
        self.clock = pygame.time.Clock()
        self.running = True

        sprites.load_all_assets()
        self.save_data = load_save()
        self._save_error = False

        self.state = self.STATE_TITLE
        self.current_level = 1

        # 游戏实体
        self.player = None
        self.tiles = []
        self.coins = []
        self.enemies = []
        self.question_blocks = []
        self.flag = None
        self.level_time = 0.0
        self.level_width = 0
        self.camera_x = 0.0

        # 跨关卡携带状态
        self._carry_lives = INITIAL_LIVES
        self._carry_score = 0
        self._carry_coins = 0
        self._win_level = 1

        # 输入
        self.keys_pressed = {}
        self.jump_consumed = False

        # 音效
        self.sfx_queue = []
        self.audio_available = False
        self.sounds = {}
        self._init_audio()

        # 字体
        self.font_large = _make_font(72)
        self.font_medium = _make_font(48)
        self.font_small = _make_font(28)
        self.font_hud = _make_font(28)

    # ── 音频 ────────────────────────────────

    def _init_audio(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(0.4)
            self.sounds = {
                'jump': pygame.mixer.Sound(f"{AUDIO_DIR}/jump.wav"),
                'coin': pygame.mixer.Sound(f"{AUDIO_DIR}/coin.wav"),
                'hurt': pygame.mixer.Sound(f"{AUDIO_DIR}/hurt.wav"),
            }
            self.sounds['jump'].set_volume(0.6)
            self.sounds['coin'].set_volume(0.5)
            self.sounds['hurt'].set_volume(0.7)
            self.audio_available = True
        except pygame.error:
            pass

    def play_music(self):
        if not self.audio_available:
            return
        try:
            pygame.mixer.music.load(f"{AUDIO_DIR}/theme_loop.wav")
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

    def stop_music(self):
        if self.audio_available:
            pygame.mixer.music.stop()

    def play_sfx(self, name):
        if self.audio_available and name in self.sounds:
            self.sounds[name].play()

    # ── 关卡管理 ────────────────────────────

    def start_level(self, level_num, lives=None, score=None, coins=None):
        """初始化关卡。

        lives/score/coins 显式覆盖默认值:
        - 新游戏: 不传 → 用 INITIAL_LIVES / 0 / 0
        - 下一关: 传 _carry_* 值
        - 死亡重开: 传已扣减的 lives + 当前 score/coins
        """
        level_info = LEVELS[level_num]
        parsed = parse_level(level_info['map'])

        self.player = Player(*parsed['player_spawn'])
        if lives is not None:
            self.player.lives = lives
        if score is not None:
            self.player.score = score
        if coins is not None:
            self.player.coins = coins

        self.tiles = parsed['tiles']
        self.coins = parsed['coins']
        self.enemies = parsed['enemies']
        self.question_blocks = parsed['question_blocks']
        self.flag = parsed['flag']
        self.level_time = float(LEVELS[level_num]['time'])
        self.level_width = parsed['width']
        self.camera_x = 0.0
        self.current_level = level_num
        self._save_error = False

    def _start_game(self, level_num, carry_over=False):
        if carry_over:
            self.start_level(level_num,
                             lives=self._carry_lives,
                             score=self._carry_score,
                             coins=self._carry_coins)
        else:
            self.start_level(level_num)
        self.state = self.STATE_PLAYING
        self.play_music()

    def _restart_same_level(self):
        """死亡后重开当前关卡, 保留已扣减的生命和当前分数。"""
        self.start_level(self.current_level,
                         lives=self.player.lives,
                         score=self.player.score,
                         coins=self.player.coins)
        self.play_music()

    # ── 状态分发 ────────────────────────────

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == self.STATE_TITLE:
                self._handle_title(event)
            elif self.state == self.STATE_LEVEL_SELECT:
                self._handle_level_select(event)
            elif self.state == self.STATE_PLAYING:
                self._handle_playing(event)
            elif self.state == self.STATE_PAUSED:
                self._handle_paused(event)
            elif self.state == self.STATE_WIN:
                self._handle_win_screen(event)
            elif self.state == self.STATE_GAME_OVER:
                self._handle_game_over(event)

    def update(self, dt):
        if self.state == self.STATE_PLAYING:
            self._update_playing(dt)

    def draw(self):
        if self.state == self.STATE_TITLE:
            self._draw_title()
        elif self.state == self.STATE_LEVEL_SELECT:
            self._draw_level_select()
        elif self.state == self.STATE_PLAYING:
            self._draw_playing()
        elif self.state == self.STATE_PAUSED:
            self._draw_paused()
        elif self.state == self.STATE_WIN:
            self._draw_win_screen()
        elif self.state == self.STATE_GAME_OVER:
            self._draw_game_over()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/game.py
git commit -m "feat: add game skeleton with state machine, audio, and CJK fonts"
```

---

### Task 9: game.py — TITLE + LEVEL_SELECT 状态

**Files:**
- Modify: `super_mario/game.py` (追加方法到 Game 类)

- [ ] **Step 1: 追加 TITLE 和 LEVEL_SELECT 方法**

```python
    # ── TITLE ───────────────────────────────

    def _handle_title(self, event):
        if event.type == pygame.KEYDOWN:
            self.stop_music()
            self.state = self.STATE_LEVEL_SELECT

    def _draw_title(self):
        self.screen.fill((40, 40, 80))
        title = self.font_large.render("Super Mario Adventure", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 180))
        sub = self.font_small.render("A/D 移动   Space/↑ 跳跃   ESC 暂停   R 重开", True, (200, 200, 200))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 280))
        start = self.font_medium.render("按任意键开始", True, (255, 255, 0))
        self.screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 400))

    # ── LEVEL SELECT ────────────────────────

    def _handle_level_select(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_TITLE
            elif event.key == pygame.K_1 and self.save_data['unlocked_level'] >= 1:
                self._start_game(1, carry_over=False)
            elif event.key == pygame.K_2 and self.save_data['unlocked_level'] >= 2:
                self._start_game(2, carry_over=False)
            elif event.key == pygame.K_3 and self.save_data['unlocked_level'] >= 3:
                self._start_game(3, carry_over=False)

    def _draw_level_select(self):
        self.screen.fill((20, 40, 60))
        title = self.font_large.render("选择关卡", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 60))

        for i in range(1, 4):
            y = 160 + (i - 1) * 130
            unlocked = self.save_data['unlocked_level'] >= i
            color = (255, 255, 255) if unlocked else (100, 100, 100)
            name = LEVELS[i]['name']
            best = self.save_data['best_scores'].get(f'level_{i}', 0)

            text = f"按 {i} - {name}"
            line1 = self.font_medium.render(text, True, color)
            self.screen.blit(line1, (SCREEN_WIDTH // 2 - line1.get_width() // 2, y))

            status = f"最高分: {best}" if unlocked else "未解锁"
            line2 = self.font_small.render(status, True, color)
            self.screen.blit(line2, (SCREEN_WIDTH // 2 - line2.get_width() // 2, y + 45))

        tip = self.font_small.render("ESC 返回标题", True, (150, 150, 150))
        self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 560))
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/game.py
git commit -m "feat: add TITLE and LEVEL_SELECT screens"
```

---

### Task 10: game.py — PLAYING 状态（游戏主体）

**Files:**
- Modify: `super_mario/game.py` (追加方法到 Game 类)

- [ ] **Step 1: 追加 PLAYING 方法**

注意: `update_player` 现在返回 `hit_blocks` 列表，传给 `handle_top_collisions`。

```python
    # ── PLAYING ─────────────────────────────

    def _handle_playing(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_PAUSED
                return
            if event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)
                return
            if event.key in (pygame.K_SPACE, pygame.K_UP):
                self.jump_consumed = False
            self.keys_pressed[event.key] = True
        elif event.type == pygame.KEYUP:
            self.keys_pressed[event.key] = False

    def _update_playing(self, dt):
        move_left = self.keys_pressed.get(pygame.K_a, False) or self.keys_pressed.get(pygame.K_LEFT, False)
        move_right = self.keys_pressed.get(pygame.K_d, False) or self.keys_pressed.get(pygame.K_RIGHT, False)
        jump_key = self.keys_pressed.get(pygame.K_SPACE, False) or self.keys_pressed.get(pygame.K_UP, False)
        if not jump_key:
            self.jump_consumed = False
        jump_pressed = jump_key and not self.jump_consumed
        if jump_pressed:
            self.jump_consumed = True

        # 物理 (返回顶到的问号砖块)
        hit_blocks = update_player(self.player, self.tiles, self.question_blocks,
                                   dt, move_left, move_right, jump_pressed)

        # 问号砖块奖励
        rewards = handle_top_collisions(self.player, hit_blocks)
        for r in rewards:
            self.sfx_queue.append('coin' if r == 'coin' else 'life')

        # 金币
        collected = handle_coin_collisions(self.player, self.coins)
        if collected > 0:
            self.sfx_queue.extend(['coin'] * collected)

        # 敌人
        update_enemies(self.enemies, self.tiles, dt)
        result = handle_enemy_collisions(self.player, self.enemies)
        if result == 'stomp':
            self.sfx_queue.append('stomp')
        elif result == 'hurt':
            self.sfx_queue.append('hurt')

        # 终点旗
        if handle_flag_collision(self.player, self.flag):
            self._on_win()

        # 倒计时
        self.level_time -= dt
        if self.level_time <= 0:
            self._on_death()

        # 掉落
        if not self.player.alive:
            self.player.alive = True
            self._on_death()

        # 问号砖块弹跳衰减
        for qb in self.question_blocks:
            if qb.bounce_offset > 0:
                qb.bounce_offset = max(0.0, qb.bounce_offset - 20.0 * dt)

        # 摄像机
        target_cx = self.player.x - SCREEN_WIDTH // 2 + TILE_SIZE // 2
        target_cx = max(0.0, min(target_cx, self.level_width - SCREEN_WIDTH))
        self.camera_x += (target_cx - self.camera_x) * min(dt * 8.0, 1.0)

        # 音效
        for sfx in self.sfx_queue:
            if sfx == 'stomp':
                self.play_sfx('jump')
            else:
                self.play_sfx(sfx)
        self.sfx_queue.clear()

    def _on_death(self):
        self.player.lives -= 1
        if self.player.lives <= 0:
            self.state = self.STATE_GAME_OVER
        else:
            self._restart_same_level()

    def _draw_playing(self):
        sprites.draw_background(self.screen, self.current_level)
        sprites.draw_tiles(self.screen, self.tiles, self.camera_x)
        sprites.draw_question_blocks(self.screen, self.question_blocks, self.camera_x)
        sprites.draw_coins(self.screen, self.coins, self.camera_x)
        sprites.draw_enemies(self.screen, self.enemies, self.camera_x)
        sprites.draw_flag(self.screen, self.flag, self.camera_x)
        sprites.draw_player(self.screen, self.player, self.camera_x)
        sprites.draw_hud(self.screen, self.player, self.level_time, self.font_hud)
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/game.py
git commit -m "feat: add PLAYING state with full gameplay loop"
```

---

### Task 11: game.py — PAUSED, WIN, GAME_OVER 状态

**Files:**
- Modify: `super_mario/game.py` (追加方法到 Game 类)

- [ ] **Step 1: 追加 PAUSED, WIN, GAME_OVER 方法**

```python
    # ── PAUSED ──────────────────────────────

    def _handle_paused(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_PLAYING
            elif event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)
            elif event.key == pygame.K_q:
                self.stop_music()
                self.state = self.STATE_LEVEL_SELECT

    def _draw_paused(self):
        self._draw_playing()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        title = self.font_large.render("暂停", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 150))
        opts = [
            ("ESC - 继续游戏", 250),
            ("R - 重新开始本关", 310),
            ("Q - 返回选关", 370),
        ]
        for text, y in opts:
            surf = self.font_medium.render(text, True, (255, 255, 255))
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))

    # ── WIN (内部触发) ──────────────────────

    def _on_win(self):
        self.stop_music()
        level_key = f'level_{self.current_level}'
        best = self.save_data['best_scores'].get(level_key, 0)
        if self.player.score > best:
            self.save_data['best_scores'][level_key] = self.player.score
        if self.current_level < 3:
            self.save_data['unlocked_level'] = max(
                self.save_data['unlocked_level'],
                self.current_level + 1,
            )

        if not write_save(self.save_data):
            self._save_error = True

        self._carry_lives = self.player.lives
        self._carry_score = self.player.score
        self._carry_coins = self.player.coins
        self._win_level = self.current_level
        self.state = self.STATE_WIN

    # ── WIN SCREEN ──────────────────────────

    def _handle_win_screen(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._win_level < 3:
                    self._start_game(self._win_level + 1, carry_over=True)
                else:
                    self.state = self.STATE_LEVEL_SELECT
            elif event.key == pygame.K_q:
                self.state = self.STATE_LEVEL_SELECT

    def _draw_win_screen(self):
        self.screen.fill((0, 40, 0))
        title = self.font_large.render("通关!", True, (255, 255, 0))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        score_text = self.font_medium.render(f"得分: {self.player.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 190))
        info = f"金币: {self.player.coins}   生命: {self.player.lives}"
        info_text = self.font_small.render(info, True, (255, 255, 255))
        self.screen.blit(info_text, (SCREEN_WIDTH // 2 - info_text.get_width() // 2, 240))

        if self._save_error:
            err = self.font_small.render("警告: 最高分保存失败", True, (255, 100, 100))
            self.screen.blit(err, (SCREEN_WIDTH // 2 - err.get_width() // 2, 280))

        if self._win_level < 3:
            tip = self.font_medium.render("按 Enter 进入下一关", True, (255, 255, 255))
            self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 350))
            tip2 = self.font_small.render("按 Q 返回选关", True, (150, 150, 150))
            self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, 400))
        else:
            tip = self.font_medium.render("恭喜全部通关!", True, (255, 255, 0))
            self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 350))
            tip2 = self.font_small.render("按 Enter 或 Q 返回选关", True, (150, 150, 150))
            self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, 400))

    # ── GAME OVER ───────────────────────────

    def _handle_game_over(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)
            elif event.key == pygame.K_q:
                self.state = self.STATE_LEVEL_SELECT

    def _draw_game_over(self):
        self.screen.fill((40, 0, 0))
        title = self.font_large.render("Game Over", True, (255, 50, 50))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 180))
        score_text = self.font_medium.render(f"最终得分: {self.player.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 280))
        tip = self.font_medium.render("按 R 重新开始", True, (255, 255, 255))
        self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 370))
        tip2 = self.font_small.render("按 Q 返回选关", True, (150, 150, 150))
        self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, 420))
```

- [ ] **Step 2: 提交**

```bash
git add super_mario/game.py
git commit -m "feat: add PAUSED, WIN, GAME_OVER screens"
```

---

### Task 12: main.py — 入口文件

**Files:**
- Create: `main.py`

- [ ] **Step 1: 写入入口文件**

```python
"""Super Mario Adventure - 课程作业入口。"""
from super_mario.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add main.py
git commit -m "feat: add entry point main.py"
```

---

### Task 13: 运行验证与 Bug 修复

- [ ] **Step 1: 运行单元测试**

```bash
cd "D:\Desktop\workspace\SuperMario" && python -m pytest tests/test_core.py -v
```
Expected: 22 tests PASS

- [ ] **Step 2: 启动游戏并手动验证**

```bash
cd "D:\Desktop\workspace\SuperMario" && python main.py
```

检查清单:
1. [ ] 标题画面正常 → 按任意键 → 选关画面 (中文正常渲染)
2. [ ] 选关画面 → 按 1 → 第 1 关开始, 背景音乐
3. [ ] A/D 移动, Space 跳跃, 碰撞地面/砖块正常
4. [ ] 金币收集: 碰到消失 +100 分 + 音效
5. [ ] 踩踏蘑菇敌人: +300 分 + 敌人消失 + 反弹
6. [ ] 侧碰敌人: -1 命 + 闪烁无敌 + 受伤音效
7. [ ] 问号砖块 (第 3 关): 从下方顶击, 随机出金币/加命, 变灰, 仍为固体
8. [ ] ESC 暂停 → 继续 / 重开 / 返回选关
9. [ ] 到达终点旗 → 通关画面 → Enter 进下一关 (保留分数/生命)
10. [ ] 时间归零 → 扣 1 命 → 重开当前关 (生命不回复)
11. [ ] 掉落底部 → 扣 1 命 → 重开当前关
12. [ ] 生命归零 → Game Over → R 重开 / Q 返回
13. [ ] 通关第 1 关 → 第 2 关解锁; 第 3 关同
14. [ ] 退出重启 → 存档保留解锁状态和最高分
15. [ ] 第 3 关通关 → "恭喜全部通关!" → 返回选关
16. [ ] 选关界面中文字体和最高分显示正常

- [ ] **Step 3: 修复发现的问题**

根据测试结果调整。

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "fix: gameplay polish and bug fixes"
```

---

### Task 14: GitHub 仓库创建与推送

- [ ] **Step 1: 更新 README.md**

在现有 README.md 末尾追加:

```markdown

## 关于本项目

本项目是 Python 课程作业，实现了一个超级马里奥风格的横版平台跳跃小游戏。

- **技术栈**: Python 3.10+ / Pygame 2.x
- **玩法**: 3 个关卡, 收集金币, 击败敌人, 到达终点旗通关
- **素材**: 原创像素风图片和 8-bit 音频
- **存档**: 最高分和关卡解锁进度持久化
```

- [ ] **Step 2: 提交 README 更新并推送**

```bash
git add README.md
git commit -m "docs: add project background to README"
cd "D:\Desktop\workspace\SuperMario"
gh repo create SuperMario --source=. --public --push --description="Python课程作业：超级马里奥风格横版平台跳跃小游戏"
```

- [ ] **Step 3: 确认远程仓库**

```bash
gh repo view --web
```

---

### 自审清单

| 检查项 | 状态 |
|--------|------|
| 存档函数定义在测试之前 (Task 4 Step 5 → Task 5) | ✓ |
| `update_player` 在纵向碰撞时直接返回 hit_blocks, 不依赖事后 colliderect | ✓ |
| 所有 QuestionBlock (含 triggered) 作为固体, triggered 仅控制奖励和贴图 | ✓ |
| 落地测试断言 `player.rect.bottom ≈ tile.rect.top` | ✓ |
| 中文字体: `_make_font` 优先 SysFont("Microsoft YaHei"/"SimHei"), 失败回退 Font(None) | ✓ |
| 版本号: requirements.txt `pygame>=2.0` 与技术栈 Pygame 2.x 一致 | ✓ |
| `start_level` 使用显式 `lives/score/coins` 参数, `_restart_same_level` 保留死亡后状态 | ✓ |
| `_start_game(carry_over=True)` 仅通关流程使用, 传入 `_carry_*` | ✓ |
| 背景图独立加载 (`_load_background`), 精灵图缩放 (`_load_sprite`) | ✓ |
| 存档失败显示 "警告: 最高分保存失败" | ✓ |
| 无未完成函数/思考过程文本；仅保留音频容错中的 `pass` | ✓ |
| 任务顺序: 依赖关系正确 (config → data → parser+save → tests → levels → sprites → game) | ✓ |
