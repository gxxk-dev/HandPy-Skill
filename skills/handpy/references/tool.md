# HandPy Tool 使用指南

`handpy_tool.py` 是 HandPy 板子的上位机控制工具，支持串口和 WiFi 两种传输方式。通过 `pip install -e .` 安装后，也可使用命令 `handpy-tool`。

## 导航

- 安装与命令：串口模式、WiFi 模式、端口与波特率
- 真机限制：v3 LVGL `tick()` 约束
- 协议与排障：协议细节、常见故障排查

---

## 安装

```bash
pip install -e .
# 或
uv pip install -e .
```

---

## 基础命令（串口模式）

### 文件传输

```bash
# 上传文件（上传后自动回读校验字节数）
handpy_tool.py put local.py :remote.py

# 下载文件
handpy_tool.py get :remote.py local.py

# 列出文件
handpy_tool.py ls --path /
```

`put` 上传后会自动回读板子上的文件大小并与本地比对，不一致会直接报错退出并给出缺了多少字节。
板子偶尔会因为串口丢字节写出残缺文件，这种情况下复位后程序会起不来，而上传命令本身却"成功"返回。
需要跳过校验时用 `--no-verify`（例如往 RAM 目标写临时文件时）。

### 运行代码

```bash
# 执行代码字符串
handpy_tool.py run --code "from mpython import *; rgb[0]=(255,0,0); rgb.write()"

# 运行本地文件
handpy_tool.py run --file script.py

# 长时间运行的脚本：默认一直等到脚本结束，不因静默超时被杀
handpy_tool.py run --file calibrate.py

# 板端脚本要读人工输入时，转发本地 stdin
handpy_tool.py run --file menu.py --stdin

# 限定最长等待时间（秒，按"板子静默"计）
handpy_tool.py run --file collect.py --timeout 300
```

`run` 以流式方式执行：板子的输出边跑边打印，长时间没有输出的脚本不会被误判失败。
需要按人机交互方式跑脚本时，要么加 `--stdin`，要么把脚本写进 `boot.py` / `main.py` 走开机自启。

### 复位板子

```bash
# 硬复位（RTS 拉 EN 引脚）
handpy_tool.py reset

# 轻量复位 + 自定义复位后等待秒数
handpy_tool.py reset --soft --delay 5
```

`boot.py` / `main.py` 里的自启死循环会独占串口，此时 `run` / `put` / `get` 全部报
`could not enter raw repl`，且反复尝试 `enter_raw_repl()` 也抢不回来。
用 `reset` 做一次物理复位，趁启动窗口期抢回控制权；若复位无效，就手动按板子上的 RST 键。

### 读取屏幕

```bash
# 自动检测版本
handpy_tool.py screen

# 或手动指定版本
handpy_tool.py screen --version v2  # v2 OLED（输出 ASCII art）
handpy_tool.py screen --version v3  # v3 LCD（输出 LVGL 组件树 JSON）

# 保存到文件
handpy_tool.py screen --out screen.txt
```

### 模拟输入

```bash
# 模拟按键
handpy_tool.py press --button A
handpy_tool.py press --button B --hold 500  # 按住 500ms

# 模拟触摸
handpy_tool.py press --touch P
handpy_tool.py press --touch Y --hold 200
```

### 刷固件

```bash
# 自动检测芯片型号
handpy_tool.py flash --firmware firmware.bin

# 或手动指定芯片
handpy_tool.py flash --firmware firmware_v2.bin --chip esp32
handpy_tool.py flash --firmware firmware_v3.bin --chip esp32s3
```

---

## WiFi 模式

WiFi 模式允许在板子运行程序时通过网络执行操作，不会中断主程序。

### 1. 部署 WiFi 服务

```bash
# 上传 handpy_server.py 到板子，并注入 boot.py
handpy_tool.py install
```

### 2. 配置 WiFi 凭据

```bash
# 添加 WiFi
handpy_tool.py wifi add --ssid "MyWiFi" --pwd "password123"

# 列出已配置的 WiFi
handpy_tool.py wifi list

# 删除 WiFi
handpy_tool.py wifi remove --ssid "MyWiFi"
```

### 3. 重启板子

重启后板子会自动连接 WiFi 并启动服务，串口会输出日志：

```
[handpy_server][0] Starting...
[handpy_server][1234] Trying SSID: MyWiFi
[handpy_server][5678] Connected, IP: 192.168.1.100
[handpy_server][5680] Listening on port 9595
```

### 4. 使用 WiFi 命令

所有命令都支持 `--transport wifi --host <IP>`：

```bash
# 读取屏幕（自动检测版本）
handpy_tool.py screen --transport wifi --host 192.168.1.100

# 或手动指定版本
handpy_tool.py screen --version v2 --transport wifi --host 192.168.1.100

# 模拟按键
handpy_tool.py press --button A --transport wifi --host 192.168.1.100

# 执行代码
handpy_tool.py run --transport wifi --host 192.168.1.100 --code "print('Hello')"

# 文件传输
handpy_tool.py put local.py :remote.py --transport wifi --host 192.168.1.100
handpy_tool.py get :remote.py local.py --transport wifi --host 192.168.1.100

# 列出文件
handpy_tool.py ls --transport wifi --host 192.168.1.100
```

### 5. 卸载服务

```bash
handpy_tool.py uninstall
```

---

## v3 LVGL 线程安全注意事项

v3 的 `screen` 命令（WiFi 模式）需要主线程调用 `handpy_server.tick()`：

```python
import handpy_server
from lv_utils import event_loop

el = event_loop()

while True:
    handpy_server.tick()  # 处理屏幕读取请求
    # 你的主循环代码
    time.sleep_ms(10)
```

如果不调用 `tick()`，WiFi 读屏会超时报错。

---

## 端口和波特率

```bash
# 指定串口
handpy_tool.py run --port /dev/ttyUSB0 --code "..."

# 指定波特率（默认 115200）
handpy_tool.py run --port /dev/ttyUSB0 --baud 115200 --code "..."
```

如果不指定 `--port`，工具会自动检测串口。

---

## 协议细节

WiFi 服务使用二进制协议，端口 9595：

- 请求：`[1B cmd][4B len big-endian][payload]`
- 响应：`[1B status][4B len][payload]`，status=0 成功，status=1 错误

CMD 枚举：
- `0x01` EXEC：执行代码
- `0x02` PUT：上传文件
- `0x03` GET：下载文件
- `0x04` LS：列出目录
- `0x05` SCREEN：读取屏幕
- `0x06` PRESS：模拟输入

---

## 故障排查

**WiFi 连接失败**：
- 检查 SSID 和密码是否正确
- 确认板子和电脑在同一网络
- 查看串口日志确认连接状态

**WiFi 命令超时**：
- 确认 IP 地址正确
- 检查防火墙是否阻止端口 9595
- v3 读屏需要主循环调用 `handpy_server.tick()`

**串口找不到**：
- Linux：检查 `/dev/ttyUSB*` 或 `/dev/ttyACM*`
- 确认用户有串口权限：`sudo usermod -a -G dialout $USER`
- 手动指定：`--port /dev/ttyUSB0`

**看起来像失败、其实是正常的情况**：

- `machine.reset()` 执行后出现 `timeout waiting for first EOF reception`：这是**复位成功的信号**，
  不是错误。板子正在重启，串口随之断开，工具自然等不到结束符。
- `could not enter raw repl`：板子可能只是**还在启动**。等几秒重试即可；
  若始终不进，则说明自启脚本正独占串口，用 `handpy-tool reset` 复位。

**上传后程序起不来**：
先确认 `put` 是否报过校验错误；没有校验过就手动比对：

```bash
handpy_tool.py run --code "import os; print(os.stat('/remote.py')[6])"
wc -c local.py
```

两者不一致说明板子上是残缺文件，重新上传。
