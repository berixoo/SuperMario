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
        assert len(result['tiles']) == 7

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
        player = Player(TILE_SIZE + 2, -10)
        for _ in range(60):
            update_player(player, [], [qb], 1.0 / 60, False, False, False)
        assert player.on_ground
        assert abs(player.rect.bottom - qb.rect.top) < 1.0

    def test_hit_block_from_below_returns_block(self):
        """从下方顶到问号砖块时, update_player 返回该砖块。"""
        qb = QuestionBlock(TILE_SIZE, TILE_SIZE * 2)
        player = Player(TILE_SIZE, TILE_SIZE * 2 + TILE_SIZE)
        tiles = [Tile(TILE_SIZE, TILE_SIZE * 4)]
        for _ in range(90):
            update_player(player, tiles, [], 1.0 / 60, False, False, False)
        assert player.on_ground, "player should land before jump"
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
