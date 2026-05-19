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
    # Semi-transparent bar behind HUD
    bar = pygame.Surface((SCREEN_WIDTH, 52))
    bar.set_alpha(140)
    bar.fill((0, 0, 0))
    screen.blit(bar, (0, 0))

    score_text = font.render(f"Score: {player.score}", True, (255, 255, 255))
    screen.blit(score_text, (10, 6))
    coin_text = font.render(f"Coins: {player.coins}", True, (255, 255, 0))
    screen.blit(coin_text, (10, 30))
    mins = int(max(0, level_time_remaining) // 60)
    secs = int(max(0, level_time_remaining) % 60)
    time_text = font.render(f"Time: {mins:02d}:{secs:02d}", True, (255, 255, 255))
    screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, 6))
    lives_text = font.render(f"Lives: {player.lives}", True, (255, 80, 80))
    screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, 6))
