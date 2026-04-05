# HandPy Skill

为掌控版（HandPy/mPython）提供的 Claude Code Skill 项目，包含：
1. **硬件知识库**：补全 LLM 对 HandPy 专有硬件的知识，生成正确的 MicroPython 代码
2. **上位机工具**：让 LLM 自主控制板子（执行代码、传文件、刷固件、读屏幕、模拟输入）

支持 v2（ESP32）和 v3（ESP32-S3）两个版本。

---

## 功能特性

### 硬件知识库（Skills）

- **通用 API**：RGB LED、按键、触摸、WiFi、IO、运动传感器
- **版本专属**：v2 OLED / v3 LCD+LVGL、传感器差异、引脚分配
- **预置模块**：SIoT、超声波、红外、AI 摄像头、舵机、扩展板等
- **懒加载设计**：模块化文档，按需加载，最小化 token 占用

### 上位机工具（handpy_tool.py）

**串口模式**（通过 mpremote）：
- 执行代码、运行脚本
- 文件传输（上传/下载/列表）
- 读取屏幕（v2 ASCII art / v3 LVGL JSON）
- 模拟输入（按键/触摸）
- 刷固件

**WiFi 模式**（通过 socket 服务）：
- 所有串口功能，但不中断板子运行的程序
- 后台线程运行，主程序继续执行
- 二进制协议，零外部依赖

---

## 快速开始

### 1. 安装

```bash
git clone <repo-url>
cd HandPy-Skill
pip install -e .
```

### 2. 串口模式

```bash
# 执行代码
handpy_tool.py run --code "from mpython import *; rgb[0]=(255,0,0); rgb.write()"

# 读取屏幕
handpy_tool.py screen --version v2

# 模拟按键
handpy_tool.py press --button A
```

### 3. WiFi 模式

```bash
# 部署服务
handpy_tool.py install

# 配置 WiFi
handpy_tool.py wifi add --ssid "MyWiFi" --pwd "password"

# 重启板子，等待连接（观察串口日志获取 IP）

# 使用 WiFi 命令
handpy_tool.py screen --version v2 --transport wifi --host 192.168.1.100
handpy_tool.py press --button A --transport wifi --host 192.168.1.100
```

详细使用说明见 [`skills/handpy-tool.md`](skills/handpy-tool.md)

---

## 项目结构

```
HandPy-Skill/
├── handpy_tool.py          # 上位机控制工具
├── board/
│   └── handpy_server.py    # WiFi socket 服务（部署到板子）
├── skills/
│   ├── handpy-common.md    # 通用 API + 模块索引
│   ├── handpy-v2.md        # v2 专属硬件
│   ├── handpy-v3.md        # v3 专属硬件
│   ├── handpy-tool.md      # 工具使用指南
│   └── modules/            # 预置模块文档（11 个）
│       ├── siot.md
│       ├── hcsr04.md
│       ├── ir_remote.md
│       ├── smartcamera.md
│       ├── servo.md
│       ├── parrot.md
│       ├── bluebit.md
│       ├── xunfei.md
│       ├── mpython_ble.md
│       ├── lv_gui.md
│       └── images.md
└── pyproject.toml
```

---

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

完整差异见 [`skills/handpy-v2.md`](skills/handpy-v2.md) 和 [`skills/handpy-v3.md`](skills/handpy-v3.md)

---

## WiFi Socket 协议

端口：9595  
格式：二进制，零外部依赖（仅用 `struct`、`ubinascii`）

**请求**：`[1B cmd][4B len big-endian][payload]`  
**响应**：`[1B status][4B len][payload]`（status=0 成功，1 错误）

**CMD 枚举**：
- `0x01` EXEC：执行代码
- `0x02` PUT：上传文件
- `0x03` GET：下载文件
- `0x04` LS：列出目录
- `0x05` SCREEN：读取屏幕
- `0x06` PRESS：模拟输入

---

## 依赖

- Python ≥ 3.9
- `mpremote` ≥ 1.0（串口通信）
- `esptool` ≥ 4.0（刷固件）

---

## 官方资源

| 资源 | v2 (ESP32) | v3 (ESP32-S3) |
|------|-----------|--------------|
| GitHub | [labplus-cn/mpython](https://github.com/labplus-cn/mpython) | [labplus-cn/mpython_esp32s3](https://github.com/labplus-cn/mpython_esp32s3) |
| 文档 | [mPython.readthedocs.io](https://mPython.readthedocs.io) | [mpython-esp32s3-doc](https://mpython-esp32s3-doc.readthedocs.io/zh-cn/latest/) |
| 官网 | [mpython.cn](https://www.mpython.cn) | [mpython.cn](https://www.mpython.cn) |
| 论坛 | [labplus.cn/forum](https://www.labplus.cn/forum) | [labplus.cn/forum](https://www.labplus.cn/forum) |

---

## 不支持的板型

- labplus_1956
- labplus_classroom_kit_II
- labplus-experiment-box-2024
- mpython-classroom-kit
- labplus_Ledong_v2（v3 变体）

---

## License

MIT
