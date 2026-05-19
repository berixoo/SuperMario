"""
Super Mario Adventure — 课程作业入口文件 (main.py)
===================================================
职责: 程序启动入口, 创建 Game 实例并启动主循环。
保持入口简洁, 所有具体逻辑分散在各模块中。

启动流程:
  main() → Game.__init__() → Game.run() → 主循环开始
    │            │                 │
    │            ├─ 初始化 Pygame    ├─ handle_events()
    │            ├─ 加载素材        ├─ update(dt)
    │            ├─ 读取存档        └─ draw()
    │            └─ 设置字体/音频
    └─ pygame.quit() / sys.exit()

运行方式:
  python main.py

打包方式 (PyInstaller 单文件):
  pyinstaller --onefile --name SuperMario \
    --add-data "assets;assets" \
    --add-data "super_mario;super_mario" \
    --noconsole main.py
"""

from super_mario.game import Game


def main():
    """创建游戏实例并启动主循环。"""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
