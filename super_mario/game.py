"""
游戏主控制模块 (game.py)
=========================
职责: 游戏的总控制器, 管理状态机、主循环、输入处理、音效调度。
- 连接 core.py (规则) 和 sprites.py (显示), 是程序的"大脑"
- 不实现底层规则 (由 core.py 负责), 不负责图片加载 (由 sprites.py 负责)

六大状态及流转:
  TITLE  ──按任意键──→  LEVEL_SELECT
                             │ 按 1/2/3
                             ↓
  GAME_OVER ←──生命归零── PLAYING ──到达终点旗──→  WIN
     │           ↑ 暂停/继续     │                    │
     │           └──ESC── PAUSED  │                    │
     │  R 重开                    │                    │ Enter/Q
     └──────── Q 返回 ─────── LEVEL_SELECT ←─────────┘

主循环流程 (每帧):
  1. handle_events() — 读取键盘/窗口事件, 分发到当前状态的处理函数
  2. update(dt)       — 更新游戏逻辑 (物理/碰撞/AI/计时)
  3. draw()            — 绘制当前状态的画面
  4. clock.tick(FPS)   — 控制帧率, 返回 dt (帧间隔秒数)

为什么 dt 很重要?
  如果不用 dt, 游戏速度会随帧率变化: 60fps 的电脑比 30fps 的快一倍。
  所有运动 (移动/重力/计时) 乘以 dt 后, 不同帧率下游戏速度一致。
  dt 上限 0.05s — 防止卡顿时一帧跳太大距离导致穿墙。
"""

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


# ═══════════════════════════════════════════════════════════════════
# 字体创建辅助函数 (模块级, 在 Game 类外部)
# ═══════════════════════════════════════════════════════════════════

def _make_font(size):
    """创建可渲染中文的 Pygame 字体。

    字体选择策略:
      1. 优先尝试 Windows 常用中文字体: Microsoft YaHei (微软雅黑), SimHei (黑体)
      2. 其次尝试跨平台中文字体: Noto Sans CJK SC
      3. 再尝试通用西文字体: Arial (如无中文需求)
      4. 全部失败后使用 Pygame 默认字体 (可能无法显示中文, 但游戏不崩溃)

    使用 match_font() 验证字体确实存在, 避免 SysFont 返回 fallback 导致方框。
    """
    for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial"]:
        matched = pygame.font.match_font(name)
        if matched:
            return pygame.font.Font(matched, size)
    return pygame.font.Font(None, size)  # 最后兜底


# ═══════════════════════════════════════════════════════════════════
# Game 类: 整个游戏的核心控制器
# ═══════════════════════════════════════════════════════════════════

class Game:
    """游戏主控制器, 管理状态机、主循环、资源调度。"""

    # ── 状态常量 ────────────────────────────
    STATE_TITLE = 'title'
    STATE_LEVEL_SELECT = 'level_select'
    STATE_PLAYING = 'playing'
    STATE_PAUSED = 'paused'
    STATE_WIN = 'win'
    STATE_GAME_OVER = 'game_over'

    # ═════════════════════════════════════════════════════════════
    # __init__: 游戏初始化 — 创建窗口、加载素材、设置初始状态
    # ═════════════════════════════════════════════════════════════

    def __init__(self):
        """初始化 Pygame、创建窗口、加载资源、设置初始状态。"""

        # ── Pygame 初始化 ──
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Mario Adventure")
        self.clock = pygame.time.Clock()   # 用于控制帧率
        self.running = True                # 主循环开关

        # ── 加载素材和存档 ──
        sprites.load_all_assets()          # 预加载全部图片到缓存
        self.save_data = load_save()       # 读取最高分和关卡解锁进度
        self._save_error = False           # 存档写入失败标记

        # ── 状态初始化 ──
        self.state = self.STATE_TITLE      # 启动后进入标题画面
        self.current_level = 1             # 当前关卡编号

        # ── 游戏实体 (在 start_level() 中填充) ──
        self.player = None
        self.tiles = []
        self.coins = []
        self.enemies = []
        self.question_blocks = []
        self.flag = None
        self.level_time = 0.0
        self.level_width = 0
        self.camera_x = 0.0

        # ── 跨关卡携带状态 (通关时保存, 进入下一关时恢复) ──
        self._carry_lives = INITIAL_LIVES
        self._carry_score = 0
        self._carry_coins = 0
        self._win_level = 1

        # ── 输入状态 (跟踪按键按下/释放) ──
        self.keys_pressed = {}             # key_code → bool
        self.jump_consumed = False         # 防止按住跳跃键连续触发

        # ── 音效系统 ──
        self.sfx_queue = []               # 本帧待播放的音效列表
        self.audio_available = False       # 音频设备可用标记
        self.sounds = {}
        self._init_audio()

        # ── 字体 (四种大小, 不同场景使用) ──
        self.font_large = _make_font(72)   # 标题文字
        self.font_medium = _make_font(48)  # 菜单选项
        self.font_small = _make_font(28)   # 说明文字
        self.font_hud = _make_font(28)     # HUD 文字


    # ═════════════════════════════════════════════════════════════
    # 音频系统: 背景音乐和音效
    # ═════════════════════════════════════════════════════════════

    def _init_audio(self):
        """初始化音频系统。如果设备不可用, 游戏继续但无声音 (不崩溃)。"""
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(0.4)  # 背景音乐 40% 音量
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
            pass  # 音频不可用时静默跳过, 游戏主体正常运行

    def play_music(self):
        """开始循环播放背景音乐。每次调用重新加载 (支持切关换曲)。"""
        if not self.audio_available:
            return
        try:
            pygame.mixer.music.load(f"{AUDIO_DIR}/theme_loop.wav")
            pygame.mixer.music.play(-1)   # -1 = 无限循环
        except pygame.error:
            pass

    def stop_music(self):
        """停止背景音乐。用于切换状态时 (通关/暂停/标题画面)。"""
        if self.audio_available:
            pygame.mixer.music.stop()

    def play_sfx(self, name):
        """播放指定音效 (jump/coin/hurt)。"""
        if self.audio_available and name in self.sounds:
            self.sounds[name].play()


    # ═════════════════════════════════════════════════════════════
    # 关卡管理: 初始化、开始、重开
    # ═════════════════════════════════════════════════════════════

    def start_level(self, level_num, lives=None, score=None, coins=None):
        """初始化/重置指定关卡。

        参数设计 (显式传参, 避免隐式 _carry 检查):
          lives=None  → 使用 Player 默认值 (INITIAL_LIVES)
          lives=3    → 覆盖为 3 (死亡重开保留扣减后的生命)
          lives=5    → 覆盖为 5 (跨关卡携带上一关的生命)

        调用场景:
          新游戏:      start_level(1)                    → 默认生命/分数
          死亡重开:    start_level(n, lives=2, score=50)  → 保留状态
          下一关:      start_level(n+1, lives=3, score=100) → 携带状态
        """
        level_info = LEVELS[level_num]
        parsed = parse_level(level_info['map'])

        # 创建玩家 (在出生点)
        self.player = Player(*parsed['player_spawn'])
        if lives is not None:
            self.player.lives = lives
        if score is not None:
            self.player.score = score
        if coins is not None:
            self.player.coins = coins

        # 填充关卡实体
        self.tiles = parsed['tiles']
        self.coins = parsed['coins']
        self.enemies = parsed['enemies']
        self.question_blocks = parsed['question_blocks']
        self.flag = parsed['flag']
        self.level_time = float(LEVELS[level_num]['time'])
        self.level_width = parsed['width']
        self.camera_x = 0.0              # 摄像机从关卡最左端开始
        self.current_level = level_num
        self._save_error = False         # 重置存档错误标记

    def _start_game(self, level_num, carry_over=False):
        """从菜单进入游戏。carry_over=True 时继承上一关的状态。

        进入前清空按键状态, 防止上一关残留的按键导致自动移动。
        """
        if carry_over:
            self.start_level(level_num,
                             lives=self._carry_lives,
                             score=self._carry_score,
                             coins=self._carry_coins)
        else:
            self.start_level(level_num)
        # 清空输入状态 — 关键! 防止换关时残留按键
        self.keys_pressed.clear()
        self.jump_consumed = False
        self.state = self.STATE_PLAYING
        self.play_music()

    def _restart_same_level(self):
        """死亡后重开当前关卡, 保留已扣减的生命和当前分数。"""
        self.start_level(self.current_level,
                         lives=self.player.lives,
                         score=self.player.score,
                         coins=self.player.coins)
        self.keys_pressed.clear()
        self.jump_consumed = False
        self.play_music()


    # ═════════════════════════════════════════════════════════════
    # TITLE 标题画面
    # ═════════════════════════════════════════════════════════════

    def _handle_title(self, event):
        """标题画面: 按任意键进入选关。"""
        if event.type == pygame.KEYDOWN:
            self.stop_music()
            self.state = self.STATE_LEVEL_SELECT

    def _draw_title(self):
        """绘制标题画面: 游戏名 + 操作说明 + 开始提示。"""
        self.screen.fill((25, 25, 55))  # 深蓝紫背景
        # 游戏标题 (白色, 大字体)
        title = self.font_large.render("Super Mario Adventure", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))
        # 操作说明 (浅灰色, 小字体)
        sub = self.font_small.render("A/D 移动   Space/↑ 跳跃   ESC 暂停   R 重开", True, (180, 180, 200))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 300))
        # 开始提示 (金黄色, 中字体, 醒目)
        start = self.font_medium.render("按任意键开始", True, (255, 230, 50))
        self.screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 430))


    # ═════════════════════════════════════════════════════════════
    # LEVEL_SELECT 选关画面
    # ═════════════════════════════════════════════════════════════

    def _handle_level_select(self, event):
        """选关画面: 1/2/3 选关, ESC 返回标题。只能选已解锁关卡。"""
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
        """绘制选关画面: 3 个关卡卡片, 显示名称/最高分/锁定状态。"""
        self.screen.fill((15, 30, 50))  # 深蓝背景
        # 标题
        title = self.font_large.render("选择关卡", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        # 3 个关卡卡片, 每个卡片: 关卡名 (中字体) + 最高分/锁定 (小字体)
        for i in range(1, 4):
            y = 150 + (i - 1) * 140  # 每卡间距 140px
            unlocked = self.save_data['unlocked_level'] >= i
            color = (255, 255, 255) if unlocked else (100, 100, 100)  # 未解锁用灰色
            name = LEVELS[i]['name']
            best = self.save_data['best_scores'].get(f'level_{i}', 0)

            # 第一行: 按键提示 + 关卡名
            text = f"按 {i} - {name}"
            line1 = self.font_medium.render(text, True, color)
            self.screen.blit(line1, (SCREEN_WIDTH // 2 - line1.get_width() // 2, y))

            # 第二行: 最高分 或 "未解锁"
            status = f"最高分: {best}" if unlocked else "未解锁"
            line2 = self.font_small.render(status, True, color)
            self.screen.blit(line2, (SCREEN_WIDTH // 2 - line2.get_width() // 2, y + 55))

        # 底部提示
        tip = self.font_small.render("ESC 返回标题", True, (120, 120, 130))
        self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 565))


    # ═════════════════════════════════════════════════════════════
    # PLAYING 游戏主体 — 核心游戏循环
    # ═════════════════════════════════════════════════════════════

    def _handle_playing(self, event):
        """游戏中的键盘事件处理。

        设计要点:
          - KEYDOWN 记录按键状态 (持续按住检测)
          - KEYUP 清除按键状态
          - Space/↑ 按下时重置 jump_consumed, 允许新一次跳跃
          - ESC 暂停, R 重开
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_PAUSED
                return
            if event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)
                return
            if event.key in (pygame.K_SPACE, pygame.K_UP):
                self.jump_consumed = False         # 新按键可触发跳跃
            self.keys_pressed[event.key] = True    # 记录按键按下
        elif event.type == pygame.KEYUP:
            self.keys_pressed[event.key] = False   # 记录按键释放

    def _update_playing(self, dt):
        """游戏主体更新 — 每帧调用一次, 处理所有游戏逻辑。

        执行顺序 (精心排列, 确保逻辑正确):
          1. 读取输入 → 2. 物理更新 → 3. 问号砖块奖励 →
          4. 金币收集 → 5. 敌人更新与碰撞 → 6. 终点旗检测 →
          7. 倒计时/掉落死亡 → 8. 敌人伤害致死检查 →
          9. 弹跳动画衰减 → 10. 摄像机跟随 → 11. 音效播放
        """

        # ── 1. 读取输入 ──
        move_left = self.keys_pressed.get(pygame.K_a, False) or self.keys_pressed.get(pygame.K_LEFT, False)
        move_right = self.keys_pressed.get(pygame.K_d, False) or self.keys_pressed.get(pygame.K_RIGHT, False)
        jump_key = self.keys_pressed.get(pygame.K_SPACE, False) or self.keys_pressed.get(pygame.K_UP, False)
        # 跳跃上升沿检测: 按键按下 → jump_consumed=False → 触发跳跃 → 标记已消耗
        if not jump_key:
            self.jump_consumed = False
        jump_pressed = jump_key and not self.jump_consumed
        if jump_pressed:
            self.jump_consumed = True

        # ── 2. 玩家物理更新 (碰撞 + 问号砖块检测) ──
        hit_blocks = update_player(self.player, self.tiles, self.question_blocks,
                                   dt, move_left, move_right, jump_pressed)

        # ── 3. 问号砖块奖励发放 ──
        rewards = handle_top_collisions(self.player, hit_blocks)
        for r in rewards:
            self.sfx_queue.append('coin' if r == 'coin' else 'life')

        # ── 4. 金币收集 ──
        collected = handle_coin_collisions(self.player, self.coins)
        if collected > 0:
            self.sfx_queue.extend(['coin'] * collected)

        # ── 5. 敌人 AI 更新 + 玩家-敌人碰撞 ──
        update_enemies(self.enemies, self.tiles, dt)
        result = handle_enemy_collisions(self.player, self.enemies)
        if result == 'stomp':
            self.sfx_queue.append('stomp')  # 踩踏音效 (复用 jump.wav)
        elif result == 'hurt':
            self.sfx_queue.append('hurt')   # 受伤音效

        # ── 6. 终点旗检测 ──
        if handle_flag_collision(self.player, self.flag):
            self._on_win()                  # 通关处理

        # ── 7. 倒计时 & 掉落死亡 (同一帧只触发一次) ──
        self.level_time -= dt
        dead_this_frame = False
        if self.level_time <= 0:
            self._on_death()
            dead_this_frame = True

        if not dead_this_frame and not self.player.alive:
            self.player.alive = True        # 重置标记
            self._on_death()

        # ── 8. 敌人伤害致生命归零检查 ──
        # handle_enemy_collisions 直接扣命, 此处补充检查 (不在 _on_death 覆盖范围内)
        if self.player.lives <= 0 and self.state == self.STATE_PLAYING:
            self.stop_music()
            self.state = self.STATE_GAME_OVER

        # ── 9. 问号砖块弹跳动画衰减 ──
        for qb in self.question_blocks:
            if qb.bounce_offset > 0:
                qb.bounce_offset = max(0.0, qb.bounce_offset - 20.0 * dt)

        # ── 10. 摄像机平滑跟随玩家 ──
        # 目标: 玩家在屏幕中央偏左 (TILE_SIZE//2 微调)
        target_cx = self.player.x - SCREEN_WIDTH // 2 + TILE_SIZE // 2
        # 限制摄像机范围: 不超过地图边界
        target_cx = max(0.0, min(target_cx, self.level_width - SCREEN_WIDTH))
        # 平滑插值 (lerp): 每帧向目标移动 dt*8 的比例 (8 = 响应速度)
        self.camera_x += (target_cx - self.camera_x) * min(dt * 8.0, 1.0)

        # ── 11. 音效播放 (消费本帧积累的音效队列) ──
        for sfx in self.sfx_queue:
            if sfx == 'stomp':
                self.play_sfx('jump')   # 踩踏使用跳跃音效
            else:
                self.play_sfx(sfx)
        self.sfx_queue.clear()

    def _on_death(self):
        """死亡处理: 扣 1 命 → 归零则 Game Over, 否则重开当前关。"""
        self.player.lives -= 1
        if self.player.lives <= 0:
            self.stop_music()
            self.state = self.STATE_GAME_OVER
        else:
            self._restart_same_level()

    def _draw_playing(self):
        """绘制游戏画面 — 按从远到近的顺序 (背景 → 砖块 → 实体 → 玩家 → HUD)。"""
        sprites.draw_background(self.screen, self.current_level)
        sprites.draw_tiles(self.screen, self.tiles, self.camera_x)
        sprites.draw_question_blocks(self.screen, self.question_blocks, self.camera_x)
        sprites.draw_coins(self.screen, self.coins, self.camera_x)
        sprites.draw_enemies(self.screen, self.enemies, self.camera_x)
        sprites.draw_flag(self.screen, self.flag, self.camera_x)
        sprites.draw_player(self.screen, self.player, self.camera_x)
        sprites.draw_hud(self.screen, self.player, self.level_time, self.font_hud)


    # ═════════════════════════════════════════════════════════════
    # PAUSED 暂停画面
    # ═════════════════════════════════════════════════════════════

    def _handle_paused(self, event):
        """暂停画面: ESC 继续, R 重开, Q 返回选关。"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_PLAYING      # 回到游戏
            elif event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)  # 重新开始
            elif event.key == pygame.K_q:
                self.stop_music()
                self.state = self.STATE_LEVEL_SELECT  # 返回选关

    def _draw_paused(self):
        """绘制暂停画面: 游戏画面 + 半透明遮罩 + 暂停菜单。"""
        # 先绘制底层游戏画面
        self._draw_playing()
        # 半透明黑色遮罩 (不透明度 180/255 ≈ 70%)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        # 暂停标题
        title = self.font_large.render("暂停", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 120))
        # 三个选项 (纵向排列, 间距 80px)
        opts = [
            ("ESC - 继续游戏", 260),
            ("R - 重新开始本关", 340),
            ("Q - 返回选关", 420),
        ]
        for text, y in opts:
            surf = self.font_medium.render(text, True, (220, 220, 220))
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))


    # ═════════════════════════════════════════════════════════════
    # WIN 通关处理 & 通关画面
    # ═════════════════════════════════════════════════════════════

    def _on_win(self):
        """通关触发 (由 _update_playing 中终点旗碰撞调用)。

        处理流程:
          1. 停止音乐
          2. 更新最高分 (如果有突破)
          3. 解锁下一关 (如果是第 1/2 关)
          4. 写入存档 (失败则标记 _save_error 用于界面提示)
          5. 保存跨关卡携带状态 (生命/分数/金币)
          6. 切换到 WIN 画面
        """
        self.stop_music()

        # 更新最高分
        level_key = f'level_{self.current_level}'
        best = self.save_data['best_scores'].get(level_key, 0)
        if self.player.score > best:
            self.save_data['best_scores'][level_key] = self.player.score

        # 解锁下一关
        if self.current_level < 3:
            self.save_data['unlocked_level'] = max(
                self.save_data['unlocked_level'],
                self.current_level + 1,
            )

        # 写入存档 (失败不崩溃, 仅标记并显示提示)
        if not write_save(self.save_data):
            self._save_error = True

        # 保存跨关卡状态 (进入下一关时继承)
        self._carry_lives = self.player.lives
        self._carry_score = self.player.score
        self._carry_coins = self.player.coins
        self._win_level = self.current_level
        self.state = self.STATE_WIN

    def _handle_win_screen(self, event):
        """通关画面按键: Enter/Space 进下一关, Q 返回选关。"""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._win_level < 3:
                    # 进入下一关, 携带生命和分数
                    self._start_game(self._win_level + 1, carry_over=True)
                else:
                    self.state = self.STATE_LEVEL_SELECT  # 三关全通, 返回选关
            elif event.key == pygame.K_q:
                self.state = self.STATE_LEVEL_SELECT

    def _draw_win_screen(self):
        """绘制通关画面: 标题 + 得分 + 金币/生命 + 操作提示 + (存档失败警告)。

        布局自上而下:
          通关! (大黄字)
          得分: XXX
          金币: XX  生命: XX
          [警告: 最高分保存失败] (仅存档失败时显示)
          按 Enter 进入下一关 / 恭喜全部通关!
          按 Q 返回选关
        """
        self.screen.fill((10, 30, 20))  # 深绿色背景
        # 通关标题
        title = self.font_large.render("通关!", True, (255, 220, 50))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))
        # 得分
        score_text = self.font_medium.render(f"得分: {self.player.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 200))
        # 金币 + 生命
        info = f"金币: {self.player.coins}    生命: {self.player.lives}"
        info_text = self.font_small.render(info, True, (200, 220, 200))
        self.screen.blit(info_text, (SCREEN_WIDTH // 2 - info_text.get_width() // 2, 270))
        # 存档失败警告 (仅在写入失败时显示)
        y_next = 340
        if self._save_error:
            err = self.font_small.render("警告: 最高分保存失败", True, (255, 120, 120))
            self.screen.blit(err, (SCREEN_WIDTH // 2 - err.get_width() // 2, y_next))
            y_next += 40
        # 操作提示
        if self._win_level < 3:
            tip = self.font_medium.render("按 Enter 进入下一关", True, (255, 255, 255))
            self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, y_next))
            tip2 = self.font_small.render("按 Q 返回选关", True, (150, 150, 150))
            self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, y_next + 55))
        else:
            tip = self.font_medium.render("恭喜全部通关!", True, (255, 220, 50))
            self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, y_next))
            tip2 = self.font_small.render("按 Enter 或 Q 返回选关", True, (150, 150, 150))
            self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, y_next + 55))


    # ═════════════════════════════════════════════════════════════
    # GAME_OVER 失败画面
    # ═════════════════════════════════════════════════════════════

    def _handle_game_over(self, event):
        """失败画面: R 重开当前关, Q 返回选关。"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._start_game(self.current_level, carry_over=False)
            elif event.key == pygame.K_q:
                self.state = self.STATE_LEVEL_SELECT

    def _draw_game_over(self):
        """绘制失败画面: Game Over 标题 + 最终得分 + 操作提示。"""
        self.screen.fill((30, 5, 5))  # 深红色背景
        title = self.font_large.render("Game Over", True, (255, 60, 60))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 140))
        score_text = self.font_medium.render(f"最终得分: {self.player.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 270))
        tip = self.font_medium.render("按 R 重新开始", True, (255, 255, 255))
        self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 370))
        tip2 = self.font_small.render("按 Q 返回选关", True, (150, 150, 150))
        self.screen.blit(tip2, (SCREEN_WIDTH // 2 - tip2.get_width() // 2, 440))


    # ═════════════════════════════════════════════════════════════
    # 状态分发 — 根据当前状态将事件/更新/绘制路由到对应处理函数
    # 使用显式 if-elif 而非 getattr 反射, 便于理解调用链路
    # ═════════════════════════════════════════════════════════════

    def handle_events(self):
        """主循环第一步: 处理所有 Pygame 事件, 按状态分发。"""
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
        """主循环第二步: 更新游戏逻辑 (仅 PLAYING 状态需要更新)。"""
        if self.state == self.STATE_PLAYING:
            self._update_playing(dt)

    def draw(self):
        """主循环第三步: 绘制当前状态的画面。最后调用 flip() 刷新屏幕。"""
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
        pygame.display.flip()  # 将后台绘制的内容显示到屏幕

    def run(self):
        """游戏主循环 — 程序入口, 持续运行直到 self.running 变为 False。

        每帧流程:
          dt = clock.tick(FPS) / 1000.0   获取帧间隔 (秒), 上限 0.05
          handle_events()                  处理输入
          update(dt)                       更新逻辑
          draw()                           绘制画面

        dt 上限 0.05s 的作用:
          如果电脑卡顿, 一帧可能耗时 0.1s 以上。
          直接用这么大的 dt 会导致玩家/敌人瞬移, 可能穿过砖块 (穿墙 bug)。
          限制为 0.05s 后, 即使卡顿也只是"慢动作", 不会穿墙。
        """
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)  # 帧间隔上限 50ms
            self.handle_events()
            self.update(dt)
            self.draw()

        # 退出主循环后清理
        pygame.quit()
        sys.exit()
