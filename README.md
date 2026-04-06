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

## 文档约定

- 不对普通说明项统一添加类型注解。像导航、版本判断、经验规则、能力列表这类内容，保持自然语言即可。
- 只有在文档实际描述稳定的对象结构、返回字段、配置项、参数表时，才补充类型信息。
- 需要类型时，优先使用 `字段 | 类型 | 说明` 这类轻量表格，不引入额外 schema 术语。
- 类型只写已确认且会影响使用/生成代码的部分；不确定时，写示例或直接标注“待确认”，不要臆测。
- 对数值字段，优先补充取值范围、单位或约束；范围未知时明确写“待确认”或“依模型/分辨率而定”。
- 除类型外，更优先写清 `必填/可选`、取值范围、默认值、版本适用范围。
- 版本差异和兼容性差异不等于版本信号；版本判断以 [`.claude/skills/handpy/SKILL.md`](.claude/skills/handpy/SKILL.md) 中的约定为准。

## License

MIT
