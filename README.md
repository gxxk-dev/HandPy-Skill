# HandPy Skill

Anthropic / Claude Code skill for HandPy（mPython / 掌控板）boards, with an optional host-side control tool.

支持：
- `v2`（ESP32）
- `v3`（ESP32-S3）

## Skill 入口

项目内的 Claude Code skill 位于：

- [`.claude/skills/handpy/SKILL.md`](.claude/skills/handpy/SKILL.md)
- [`.claude/skills/handpy/references/common.md`](.claude/skills/handpy/references/common.md)
- [`.claude/skills/handpy/references/v2.md`](.claude/skills/handpy/references/v2.md)
- [`.claude/skills/handpy/references/v3.md`](.claude/skills/handpy/references/v3.md)
- [`.claude/skills/handpy/references/tool.md`](.claude/skills/handpy/references/tool.md)
- [`.claude/skills/handpy/references/modules/`](.claude/skills/handpy/references/modules)

`SKILL.md` 只负责触发和导航，详细知识按需从 `references/` 加载。

## 覆盖范围

- 通用板载 API：RGB LED、按键、触摸、WiFi、IO、运动传感器
- 版本专属能力：v2 OLED / v3 LCD + LVGL、传感器差异、引脚分配
- 预置模块：SIoT、超声波、红外、AI 摄像头、舵机、扩展板、BLE、讯飞语音
- 可选真机控制：执行代码、传文件、读屏、模拟输入、刷固件

## 在 Claude Code 中使用

如果直接在本仓库里使用 Claude Code，项目级 skill 会从 `.claude/skills/handpy/` 自动生效。

如果要全局复用，可将 `.claude/skills/handpy/` 复制或软链接到 `~/.claude/skills/handpy/`。

## 可选工具

仓库同时包含主机侧控制工具：

- [handpy_tool.py](handpy_tool.py)
- [board/handpy_server.py](board/handpy_server.py)

安装：

```bash
pip install -e .
```

安装后可使用 `handpy-tool` 命令；也可以直接运行 `handpy_tool.py`。

详细命令见 [`.claude/skills/handpy/references/tool.md`](.claude/skills/handpy/references/tool.md)。

## 项目结构

```text
HandPy-Skill/
├── .claude/
│   └── skills/
│       └── handpy/
│           ├── SKILL.md
│           └── references/
│               ├── common.md
│               ├── v2.md
│               ├── v3.md
│               ├── tool.md
│               └── modules/
├── handpy_tool.py
├── board/
│   └── handpy_server.py
└── pyproject.toml
```

## 版本差异速查

| 功能 | v2 (ESP32) | v3 (ESP32-S3) |
|------|-----------|--------------|
| MicroPython | 1.12.0 | 1.24.1 |
| 可用 RAM | 约 120KB | 内部 64KB + PSRAM 8MB+ |
| 显示屏 | SSD1106 OLED 128×64 | LCD 320×172（LVGL 9.3） |
| 环境传感器 | BME280（温湿压） | LTR-308ALS（光照） |
| 音频 | 蜂鸣器 + MP3 软解码 | ES8388 编解码器 + 双麦克风 |
| Flash | 4MB | 16MB |
| f-string | ❌ | ✅ |

完整差异见 [`.claude/skills/handpy/references/v2.md`](.claude/skills/handpy/references/v2.md) 和 [`.claude/skills/handpy/references/v3.md`](.claude/skills/handpy/references/v3.md)。

## License

MIT
