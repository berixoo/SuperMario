"""
核心规则与数据结构模块 (core.py)
================================
职责: 定义所有游戏实体类和纯逻辑函数。
- 不依赖 Pygame, 可独立进行单元测试
- 所有位置/速度使用浮点数, 配合 dt 实现帧率无关运动
- 碰撞检测采用分离轴 (先横后纵) 避免穿墙和卡角

模块间关系:
  被 game.py 调用 (主循环驱动)
  被 tests/test_core.py 进行单元测试
  导入 config.py 获取常量
"""

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


# ═══════════════════════════════════════════════════════════════════
# Rect: 纯 Python 矩形类
# 替代 pygame.Rect, 使模块不依赖 Pygame, 可单独测试
# ═══════════════════════════════════════════════════════════════════
class Rect:
    """纯 Python 矩形, 用于碰撞检测 (不依赖 Pygame)。

    Pygame 坐标系: 原点在左上角, x 向右增长, y 向下增长。
    碰撞判断使用 AABB (Axis-Aligned Bounding Box) 算法:
    两个矩形相交当且仅当它们在 x 轴和 y 轴上的投影都有重叠。
    """

    def __init__(self, x, y, width, height):
        self.x = float(x)       # 左上角 x 坐标
        self.y = float(y)       # 左上角 y 坐标
        self.width = width      # 矩形宽度
        self.height = height    # 矩形高度

    # 四个边界属性: 每次计算而非存储, 保证与 x/y 保持同步
    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    def colliderect(self, other):
        """AABB 碰撞检测: 两矩形在 x 和 y 轴上投影均有重叠才碰撞。
        注意: 仅边界相邻 (如 self.right == other.left) 不算碰撞。
        """
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )


# ═══════════════════════════════════════════════════════════════════
# Player: 玩家实体
# ═══════════════════════════════════════════════════════════════════
class Player:
    """玩家角色。所有坐标和速度使用 float, 配合 dt 实现帧率无关运动。

    属性说明:
      x, y    - 左上角世界坐标 (float)
      vx, vy  - 当前速度 (px/s)
      on_ground - 是否站在地面上 (控制跳跃许可)
      facing_right - 朝向 (控制精灵图片左右翻转)
      lives   - 当前生命数
      score   - 累计分数
      coins   - 收集金币总数
      invincible_timer - 受伤后无敌倒计时 (秒)
      alive   - 是否存活 (掉落出界后变为 False)
    """

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0               # 水平速度
        self.vy = 0.0               # 垂直速度
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.on_ground = False      # 是否着地
        self.facing_right = True    # 默认朝右
        self.lives = INITIAL_LIVES
        self.score = 0
        self.coins = 0
        self.invincible_timer = 0.0 # >0 时处于无敌状态
        self.alive = True

    @property
    def rect(self):
        """返回当前包围矩形, 用于碰撞检测。"""
        return Rect(self.x, self.y, self.width, self.height)

    @property
    def invincible(self):
        """是否处于无敌状态 (受伤后短暂保护)。"""
        return self.invincible_timer > 0


# ═══════════════════════════════════════════════════════════════════
# Enemy: 敌人实体
# ═══════════════════════════════════════════════════════════════════
class Enemy:
    """敌人角色。支持两种类型:
      - 'mush' (蘑菇): 地面巡逻, 遇墙或平台边缘转向, 受重力影响
      - 'bird' (飞行): 水平飞行 + sin 波形上下浮动, 不受重力
    """

    def __init__(self, x, y, enemy_type='mush'):
        self.x = float(x)
        self.y = float(y)
        # 初始向左移动 (速度为负)
        self.vx = -MUSHROOM_SPEED if enemy_type == 'mush' else -BIRD_SPEED
        self.vy = 0.0
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.enemy_type = enemy_type   # 'mush' 或 'bird'
        self.alive = True              # 被踩踏后变为 False
        self.float_phase = 0.0         # 飞行敌人的 sin 相位 (弧度)

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════
# Coin: 金币实体
# ═══════════════════════════════════════════════════════════════════
class Coin:
    """可收集金币。玩家触碰后 collected 变为 True, 不再绘制和碰撞。"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.collected = False

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════
# QuestionBlock: 问号砖块实体
# ═══════════════════════════════════════════════════════════════════
class QuestionBlock:
    """问号砖块。玩家从下方顶击可获得随机奖励 (50% 金币 / 50% 加命)。
    触发后变为已使用状态 (灰色), 不可再次触发。
    所有问号砖块 (含已触发) 均为固体, 可站立和碰撞。
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.triggered = False          # 是否已被顶击
        self.bounce_offset = 0.0        # 弹跳动画偏移 (顶击后逐渐衰减)

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════
# Tile: 地面/砖块实体
# ═══════════════════════════════════════════════════════════════════
class Tile:
    """静态固体砖块。构成关卡的地面、墙壁和平台。"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════
# Flag: 终点旗实体
# ═══════════════════════════════════════════════════════════════════
class Flag:
    """终点旗。玩家触碰即通关。高度为 2 倍瓦片 (64px), 便于从下方跳跃触碰。"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE * 2  # 旗帜比普通方块高一倍

    @property
    def rect(self):
        return Rect(self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════
# 关卡解析函数: 将文本地图字符串转换为游戏实体列表
# ═══════════════════════════════════════════════════════════════════

def parse_level(level_text):
    """将文本关卡字符串列表解析为游戏实体字典。

    遍历二维字符网格:
      # → Tile (固体砖块)
      P → 玩家出生点坐标
      C → Coin (金币)
      E → Enemy('mush') 蘑菇敌人
      B → Enemy('bird') 飞行敌人
      Q → QuestionBlock (未触发问号砖块)
      U → QuestionBlock (已触发, triggered=True)
      F → Flag (终点旗)
      . → 跳过 (空白)

    Args:
        level_text: list[str], 每行一个等长或不等长字符串

    Returns:
        dict 包含 tiles, coins, enemies, question_blocks, flag,
             player_spawn, width, height
    """
    tiles = []
    coins = []
    enemies = []
    question_blocks = []
    flag = None
    player_spawn = (TILE_SIZE, TILE_SIZE)  # 默认出生点

    for row, line in enumerate(level_text):
        for col, char in enumerate(line):
            x = col * TILE_SIZE          # 像素坐标 = 瓦片坐标 × 瓦片尺寸
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
                # 'U' 表示已触发的问号砖块 (存在于地图初始状态)
                qb = QuestionBlock(x, y)
                qb.triggered = True
                question_blocks.append(qb)
            elif char == CHAR_FLAG:
                flag = Flag(x, y)

    # 地图宽度取最长行的列数
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


# ═══════════════════════════════════════════════════════════════════
# 玩家物理更新: 移动、重力、跳跃、碰撞解析
# ═══════════════════════════════════════════════════════════════════

def update_player(player, tiles, question_blocks, dt, move_left, move_right, jump_pressed):
    """更新玩家物理状态, 处理碰撞, 返回顶击到的问号砖块列表。

    核心设计:
      1. 所有问号砖块 (含已触发) 均为固体, 加入碰撞体列表
      2. 分离横纵轴处理碰撞 (先横后纵), 避免穿墙和卡角
      3. 纵向碰撞时, 若玩家上升且碰到 QuestionBlock, 记录到返回值
      4. 所有运动乘以 dt, 保证不同帧率下游戏速度一致

    Args:
        player: Player 实例
        tiles: list[Tile] 砖块列表
        question_blocks: list[QuestionBlock] 问号砖块列表 (全部作为固体)
        dt: 帧间隔秒数 (Pygame clock.tick 返回值 / 1000)
        move_left, move_right: bool 移动输入
        jump_pressed: bool 跳跃输入 (需在上升沿触发, 由调用方控制)

    Returns:
        list[QuestionBlock] 本帧从下方顶到的问号砖块
    """
    # ── 合并所有固体碰撞体 ──
    solids = list(tiles)
    solids.extend(question_blocks)  # 已触发的问号砖块也是固体!

    # ── 1. 水平移动 ──
    player.vx = 0.0
    if move_left:
        player.vx = -PLAYER_SPEED
        player.facing_right = False
    if move_right:
        player.vx = PLAYER_SPEED
        player.facing_right = True

    # 移动 x, 然后逐固体检查并修正 (避免穿入砖块内部)
    player.x += player.vx * dt
    for solid in solids:
        if player.rect.colliderect(solid.rect):
            if player.vx > 0:        # 向右撞墙 → 推到墙左边
                player.x = solid.rect.left - player.width
            elif player.vx < 0:      # 向左撞墙 → 推到墙右边
                player.x = solid.rect.right

    # ── 2. 重力加速度 ──
    player.vy += GRAVITY * dt
    if player.vy > MAX_FALL_SPEED:   # 限制最大下落速度 (终端速度)
        player.vy = MAX_FALL_SPEED

    # ── 3. 跳跃 ──
    if jump_pressed and player.on_ground:
        player.vy = PLAYER_JUMP_VEL
        player.on_ground = False

    # ── 4. 纵向移动 + 检测顶击问号砖块 ──
    hit_blocks = []  # 本帧顶到的问号砖块
    player.y += player.vy * dt
    player.on_ground = False
    for solid in solids:
        if player.rect.colliderect(solid.rect):
            if player.vy > 0:        # 下落 → 落到砖块顶部
                player.y = solid.rect.top - player.height
                player.vy = 0.0
                player.on_ground = True
            elif player.vy < 0:      # 上升 → 头顶撞到砖块底部
                player.y = solid.rect.bottom
                player.vy = 0.0
                # 记录从下方顶击的问号砖块 (由 handle_top_collisions 发奖励)
                if isinstance(solid, QuestionBlock):
                    hit_blocks.append(solid)

    # ── 5. 无敌计时衰减 ──
    if player.invincible_timer > 0:
        player.invincible_timer -= dt
        if player.invincible_timer < 0:
            player.invincible_timer = 0.0

    # ── 6. 掉落出界检测 ──
    # 地图底部以下 2000px 视为深渊, 玩家掉落即死亡
    if player.y > 2000:
        player.alive = False

    return hit_blocks


# ═══════════════════════════════════════════════════════════════════
# 敌人更新: AI 行为 (巡逻、转向、重力)
# ═══════════════════════════════════════════════════════════════════

def update_enemies(enemies, tiles, dt):
    """更新所有敌人的位置和 AI 行为。

    蘑菇敌人 AI:
      1. 受重力影响, 会下落到砖块上
      2. 水平匀速巡逻, 遇墙转向
      3. 到达平台边缘时转向 (防止走出平台掉落)

    飞行敌人 AI:
      1. 不受重力, 在初始高度附近浮动
      2. 使用 sin 函数实现上下波动
      3. 水平匀速飞行, 遇墙转向

    Args:
        enemies: list[Enemy]
        tiles: list[Tile]
        dt: 帧间隔秒数
    """
    tile_rects = [t.rect for t in tiles]

    for enemy in enemies:
        if not enemy.alive:        # 已死亡敌人跳过
            continue

        if enemy.enemy_type == 'mush':
            # ── 蘑菇敌人 ──

            # 重力
            enemy.vy += GRAVITY * dt
            if enemy.vy > MAX_FALL_SPEED:
                enemy.vy = MAX_FALL_SPEED

            # 水平移动 + 撞墙检测
            enemy.x += enemy.vx * dt
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vx > 0:
                        enemy.x = tr.left - enemy.width
                    elif enemy.vx < 0:
                        enemy.x = tr.right
                    enemy.vx = -enemy.vx      # 撞墙转向
                    break

            # 纵向移动 + 落地检测
            enemy.y += enemy.vy * dt
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vy > 0:
                        enemy.y = tr.top - enemy.height
                        enemy.vy = 0.0
                    elif enemy.vy < 0:
                        enemy.y = tr.bottom
                        enemy.vy = 0.0

            # 平台边缘检测: 前方一步如果没有地面, 则转向 (防止走出平台)
            edge_x = enemy.x + (enemy.width if enemy.vx > 0 else -1)
            edge_rect = Rect(edge_x, enemy.y + enemy.height + 1, 1, 1)
            on_edge = any(edge_rect.colliderect(tr) for tr in tile_rects)
            if not on_edge:
                enemy.vx = -enemy.vx

        elif enemy.enemy_type == 'bird':
            # ── 飞行敌人 ──

            # sin 波形上下浮动: 相位随时间推进, y 坐标按正弦变化
            enemy.float_phase += dt * 3.0
            enemy.x += enemy.vx * dt
            enemy.y += math.sin(enemy.float_phase) * BIRD_FLOAT_AMPLITUDE * dt * 3.0

            # 水平撞墙检测
            for tr in tile_rects:
                if enemy.rect.colliderect(tr):
                    if enemy.vx > 0:
                        enemy.x = tr.left - enemy.width
                    elif enemy.vx < 0:
                        enemy.x = tr.right
                    enemy.vx = -enemy.vx
                    break


# ═══════════════════════════════════════════════════════════════════
# 游戏规则函数: 金币收集、敌人碰撞、问号砖块奖励、终点旗
# ═══════════════════════════════════════════════════════════════════

def handle_coin_collisions(player, coins):
    """处理玩家与金币的碰撞检测和收集。

    遍历所有金币, 检查是否与玩家矩形重叠。
    收集后: 金币标记为已收集 (不再绘制), 玩家加分加币。

    Args:
        player: Player 实例
        coins: list[Coin]

    Returns:
        int: 本帧收集的金币数量 (用于触发音效)
    """
    collected = 0
    for coin in coins:
        if not coin.collected and player.rect.colliderect(coin.rect):
            coin.collected = True
            player.score += COIN_SCORE
            player.coins += 1
            collected += 1
    return collected


def handle_enemy_collisions(player, enemies):
    """处理玩家与敌人的碰撞, 区分踩踏和侧碰。

    碰撞判定逻辑:
      - 玩家处于无敌状态 → 不检测 (直接返回 None)
      - 玩家下落中 (vy > 0) 且脚底靠近敌人头顶 (距离 < 阈值) → 踩踏成功
      - 其他情况 (水平碰撞或从下方碰) → 玩家受伤

    踩踏阈值说明:
      取最大一帧下落距离的 1.5 倍, 即 MAX_FALL_SPEED * 0.05 * 1.5 ≈ 72px。
      这样即使玩家以最大速度下落, 也能正确判定踩踏而非受伤。

    Args:
        player: Player 实例
        enemies: list[Enemy]

    Returns:
        'stomp' - 踩踏成功
        'hurt'  - 玩家受伤
        None    - 无碰撞或无敌中
    """
    if player.invincible:        # 受伤后短暂无敌, 不受伤害
        return None

    for enemy in enemies:
        if not enemy.alive:      # 已死敌人跳过
            continue
        if not player.rect.colliderect(enemy.rect):
            continue

        # 踩踏判定: 玩家下落 + 脚底在敌人头顶附近
        stomp_threshold = MAX_FALL_SPEED * 0.05 * 1.5
        if player.vy > 0 and (player.rect.bottom - enemy.rect.top) < stomp_threshold:
            enemy.alive = False       # 敌人被踩死
            player.score += STOMP_SCORE
            player.vy = PLAYER_JUMP_VEL * 0.6  # 反弹 (比正常跳跃低)
            return 'stomp'
        else:
            # 侧碰或其他方向碰撞 → 受伤
            player.lives -= 1
            player.invincible_timer = INVINCIBLE_DURATION  # 启动无敌保护
            return 'hurt'

    return None


def handle_top_collisions(player, hit_blocks):
    """处理 update_player 检测到的顶击问号砖块, 发放随机奖励。

    奖励机制:
      50% 概率获得金币 (+100 分, 金币数 +1)
      50% 概率获得加命 (+1 生命)

    已触发的问号砖块跳过 (不可重复获取奖励)。

    Args:
        player: Player 实例 (用于增加分数/生命)
        hit_blocks: update_player() 返回的问号砖块列表

    Returns:
        list of ('coin' | 'life')  每项对应一个音效触发
    """
    results = []
    for qb in hit_blocks:
        if qb.triggered:           # 已触发过的跳过
            continue
        qb.triggered = True        # 标记为已触发
        qb.bounce_offset = 6.0     # 启动弹跳动画 (6px 偏移, 逐渐衰减)
        if random.random() < 0.5:  # 50% 金币
            player.score += COIN_SCORE
            player.coins += 1
            results.append('coin')
        else:                      # 50% 加命
            player.lives += 1
            results.append('life')
    return results


def handle_flag_collision(player, flag):
    """检查玩家是否到达终点旗。

    Args:
        player: Player 实例
        flag: Flag 实例或 None

    Returns:
        bool: True 表示通关
    """
    if flag is None:
        return False
    return player.rect.colliderect(flag.rect)


# ═══════════════════════════════════════════════════════════════════
# 存档系统: JSON 格式最高分和关卡解锁进度持久化
# ═══════════════════════════════════════════════════════════════════

def _default_save():
    """返回全新的默认存档结构。

    每次调用创建崭新的 dict 对象 (含嵌套 best_scores),
    避免 Python 可变默认参数陷阱 — 多个调用方不会共享同一对象。
    """
    return {
        'unlocked_level': 1,
        'best_scores': {'level_1': 0, 'level_2': 0, 'level_3': 0},
    }


def load_save():
    """从 JSON 文件读取存档, 文件不存在或损坏时返回默认值。

    容错设计:
      - 文件不存在 → 返回默认存档
      - JSON 解析失败 → 返回默认存档 (不崩溃)
      - 旧版本存档缺少字段 → 用默认值填充

    Returns:
        dict: 包含 unlocked_level 和 best_scores 的存档数据
    """
    if not os.path.exists(SAVE_FILE):
        return _default_save()
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 用默认值兜底, 再覆盖文件中的值 (向前兼容)
        result = _default_save()
        result.update(data)
        return result
    except (json.JSONDecodeError, IOError):
        return _default_save()


def write_save(data):
    """将存档数据写入 JSON 文件。

    自动创建 save 目录。写入失败返回 False, 调用方可显示提示。

    Args:
        data: dict 存档数据

    Returns:
        bool: True 表示写入成功, False 表示失败
    """
    os.makedirs(SAVE_DIR, exist_ok=True)  # 确保目录存在
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)  # 缩进 2 格, 便于人工查看
        return True
    except IOError:
        return False
