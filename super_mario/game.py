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
