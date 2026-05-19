"""
精灵显示模块 (sprites.py)
==========================
职责: 封装所有 Pygame 图片加载和绘制逻辑。
- 负责素材的加载、缓存、缩放
- 负责所有游戏实体的屏幕绘制 (含摄像机偏移)
- 负责 HUD (分数/金币/时间/生命) 的渲染

为什么分离 sprites.py 和 core.py?
  core.py 是纯 Python 规则逻辑, 不依赖 Pygame, 可单独测试。
  sprites.py 负责 Pygame 的显示部分, 将 core.py 的数据"画"到屏幕上。
  两者职责分明: core 管"规则是什么", sprites 管"怎么画出来"。

图片加载策略:
  背景图 — 保持原始尺寸加载, 绘制时缩放到窗口大小 (避免二次失真)
  精灵图 — 加载后立即缩放到 TILE_SIZE (统一尺寸, 方便碰撞对齐)

缓存机制:
  _sprites 和 _backgrounds 两个模块级字典缓存已加载的图片,
  避免每帧重复从磁盘读取, 显著提升渲染性能。
"""

import pygame
from super_mario.config import IMAGES_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

# ── 图片缓存 ──────────────────────────────────────────────────────
_sprites = {}       # 精灵图缓存: key=文件名, value=已缩放到 TILE_SIZE 的 Surface
_backgrounds = {}   # 背景图缓存: key=文件名, value=原始尺寸的 Surface


# ═══════════════════════════════════════════════════════════════════
# 内部加载函数 (模块私有, 外部通过 load_all_assets 和 draw_* 使用)
# ═══════════════════════════════════════════════════════════════════

def _load_sprite(name):
    """加载精灵图并缩放到 TILE_SIZE, 缓存结果。

    除 goal_flag.png (缩放为 TILE_SIZE×2 的旗帜高度) 外,
    所有精灵统一缩放为 TILE_SIZE×TILE_SIZE。
    """
    if name not in _sprites:
        path = f"{IMAGES_DIR}/{name}"
        img = pygame.image.load(path).convert_alpha()  # convert_alpha 保留透明通道
        if name == 'goal_flag.png':
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE * 2))
        else:
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        _sprites[name] = img
    return _sprites[name]


def _load_background(name):
    """加载背景图, 保持原始尺寸, 缓存结果。

    背景图不在加载时缩放, 而是在 draw_background 中缩放到窗口大小。
    这样避免了先缩再放的二次失真。
    """
    if name not in _backgrounds:
        path = f"{IMAGES_DIR}/{name}"
        _backgrounds[name] = pygame.image.load(path).convert()  # convert 去掉 alpha (背景不需透明)
    return _backgrounds[name]


# ═══════════════════════════════════════════════════════════════════
# 预加载函数: 游戏启动时调用一次, 加载全部素材到缓存
# ═══════════════════════════════════════════════════════════════════

def load_all_assets():
    """预加载全部精灵图和背景图, 在 Game.__init__() 中调用一次。"""
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


# ═══════════════════════════════════════════════════════════════════
# 绘制函数: 每帧由 game.py 的 _draw_playing() 按顺序调用
# 所有坐标需要减去 camera_x (摄像机水平偏移) 实现滚动
# ═══════════════════════════════════════════════════════════════════

def draw_background(screen, level_num):
    """绘制关卡背景图, 拉伸填满整个窗口。

    Args:
        screen: Pygame display surface
        level_num: 1/2/3, 决定使用哪张背景图
    """
    bg_map = {1: 'background_day.png', 2: 'background_cave.png', 3: 'background_sky_castle.png'}
    bg = _load_background(bg_map.get(level_num, 'background_day.png'))
    # 原始尺寸背景 → 缩放到窗口大小 → 铺满屏幕
    bg = pygame.transform.scale(bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(bg, (0, 0))


def draw_tiles(screen, tiles, camera_x):
    """绘制所有地面砖块 (最底层, 先绘制)。

    世界坐标 tile.x - 摄像机偏移 camera_x = 屏幕坐标。
    """
    img = _load_sprite('tile_ground.png')
    for tile in tiles:
        screen.blit(img, (tile.x - camera_x, tile.y))


def draw_coins(screen, coins, camera_x):
    """绘制所有未收集的金币 (已收集的跳过不画)。

    金币位置来自 core.Coin 实例, 由 core.parse_level() 确定。
    """
    img = _load_sprite('coin.png')
    for coin in coins:
        if not coin.collected:     # 已收集的金币不再绘制
            screen.blit(img, (coin.x - camera_x, coin.y))


def draw_enemies(screen, enemies, camera_x):
    """绘制所有存活的敌人, 根据 enemy_type 选择不同图片。

    蘑菇敌人使用 enemy_mush.png, 飞行敌人使用 enemy_bird.png。
    已死亡 (被踩踏) 的敌人跳过不画。
    """
    mush_img = _load_sprite('enemy_mush.png')
    bird_img = _load_sprite('enemy_bird.png')
    for enemy in enemies:
        if not enemy.alive:        # 已死敌人不绘制
            continue
        img = mush_img if enemy.enemy_type == 'mush' else bird_img
        screen.blit(img, (enemy.x - camera_x, enemy.y))


def draw_question_blocks(screen, question_blocks, camera_x):
    """绘制问号砖块, 根据 triggered 状态显示不同图片。

    未触发 → question_block.png (金色问号)
    已触发 → used_block.png (灰色)
    弹跳动画: y 坐标减去 bounce_offset (触发后从 6px 逐渐衰减到 0)
    """
    active_img = _load_sprite('question_block.png')
    used_img = _load_sprite('used_block.png')
    for qb in question_blocks:
        img = used_img if qb.triggered else active_img
        # bounce_offset 实现弹跳效果: 偏移逐渐衰减 → 砖块回到原位
        screen.blit(img, (qb.x - camera_x, qb.y - qb.bounce_offset))


def draw_player(screen, player, camera_x):
    """绘制玩家角色, 处理无敌闪烁和朝向切换。

    无敌闪烁: 每 100ms 切换可见/不可见 (利用 invincible_timer 计算)。
    朝向: facing_right=True → player_right.png, False → player_left.png。
    """
    # 无敌时闪烁: 每 100ms 切换一次可见性
    if player.invincible and int(player.invincible_timer * 10) % 2 == 0:
        return  # 跳过绘制 (实现闪烁效果)
    name = 'player_right.png' if player.facing_right else 'player_left.png'
    screen.blit(_load_sprite(name), (player.x - camera_x, player.y))


def draw_flag(screen, flag, camera_x):
    """绘制终点旗 (若存在)。

    flag 为 None 时跳过 (某些关卡可能没有旗, 虽然当前三关都有)。
    """
    if flag is None:
        return
    screen.blit(_load_sprite('goal_flag.png'), (flag.x - camera_x, flag.y))


def draw_hud(screen, player, level_time_remaining, font):
    """绘制游戏内抬头显示 (HUD), 包含半透明黑底条。

    布局:
      ┌────────────────────────────────────────────┐
      │ Score: XXX  Coins: YY   Time: 02:00  Lives: 3 │  ← 半透明黑底条
      └────────────────────────────────────────────┘

    设计考量:
      - 半透明黑底确保文字在各种背景上都清晰可读
      - 时间居中显示 (最关键的信息)
      - 分数/金币在左, 生命在右 (信息层次分明)
    """
    # 半透明黑底条 — 宽 800, 高 52, alpha=140 (约 55% 不透明)
    bar = pygame.Surface((SCREEN_WIDTH, 52))
    bar.set_alpha(140)
    bar.fill((0, 0, 0))
    screen.blit(bar, (0, 0))

    # 分数 (左上)
    score_text = font.render(f"Score: {player.score}", True, (255, 255, 255))
    screen.blit(score_text, (10, 6))

    # 金币 (分数下方)
    coin_text = font.render(f"Coins: {player.coins}", True, (255, 255, 0))
    screen.blit(coin_text, (10, 30))

    # 倒计时 (中上, 根据实际宽度居中)
    mins = int(max(0, level_time_remaining) // 60)
    secs = int(max(0, level_time_remaining) % 60)
    time_text = font.render(f"Time: {mins:02d}:{secs:02d}", True, (255, 255, 255))
    screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, 6))

    # 生命 (右上, 根据实际宽度右对齐)
    lives_text = font.render(f"Lives: {player.lives}", True, (255, 80, 80))
    screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, 6))
