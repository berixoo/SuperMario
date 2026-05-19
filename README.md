# Python 课程作业：超级马里奥风格小游戏方案

本项目为 Python 课程作业，实现了完整的超级马里奥风格横版平台跳跃小游戏。包含 3 个关卡、菜单系统、敌人 AI、问号砖块、倒计时和最高分存档。

游戏定位：参考经典横版平台跳跃玩法，设计一个原创像素风小游戏。角色、背景、金币、敌人、旗帜和音乐均为项目内生成的原创素材，不直接使用任天堂官方《超级马里奥》图片、音乐或商标素材。

## 快速开始

### 环境要求

- Python 3.10 或以上
- Pygame 2.x

### 拉取代码

```bash
git clone https://github.com/berixoo/SuperMario.git
cd SuperMario
```

已拉取过的仓库更新代码：

```bash
git pull origin master
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行游戏

```bash
python main.py
```

| 操作 | 按键 |
|------|------|
| 向左移动 | A / ← |
| 向右移动 | D / → |
| 跳跃 | Space / ↑ |
| 暂停 | ESC |
| 重新开始 | R |

### 运行测试

```bash
python -m pytest tests/test_core.py -v
```

### 下载可执行程序

无需安装 Python，下载解压即可运行：

[SuperMario v1.0.0](https://github.com/berixoo/SuperMario/releases/tag/v1.0.0) → 下载 `SuperMario.zip` → 解压 → 双击 `SuperMario.exe`

## 项目结构

```text
SuperMario/
├─ main.py
├─ requirements.txt
├─ README.md
├─ super_mario/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ core.py
│  ├─ level_data.py
│  ├─ sprites.py
│  └─ game.py
├─ tests/
│  ├─ __init__.py
│  └─ test_core.py
├─ docs/
│  ├─ 01_game_design.md
│  ├─ 02_implementation_plan.md
│  ├─ 03_module_function_explanation.md
│  └─ superpowers/
│     ├─ specs/2026-05-18-full-game-design.md
│     └─ plans/2026-05-18-full-game-implementation.md
└─ assets/
   ├─ README.md
   ├─ images/
   │  └─ (原创像素风素材)
   └─ audio/
      └─ (8-bit 音频)
```

## 建议开发技术

- Python 3.10+
- Pygame 2.x
- 文本关卡地图
- 面向对象组织角色、敌人、地图和游戏主循环

详细设计见 [docs/01_game_design.md](docs/01_game_design.md)。
完整设计文档见 [docs/superpowers/specs/2026-05-18-full-game-design.md](docs/superpowers/specs/2026-05-18-full-game-design.md)。
实施计划见 [docs/02_implementation_plan.md](docs/02_implementation_plan.md)。
模块讲解见 [docs/03_module_function_explanation.md](docs/03_module_function_explanation.md)。
