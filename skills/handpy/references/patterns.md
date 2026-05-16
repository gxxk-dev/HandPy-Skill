# HandPy 编程模式与优化指南

## 读取顺序

- 输入处理：用户问按键/触摸 → 读"输入模式决策"
- 异步编程：用户说阻塞/卡顿/多任务 → 读"异步推荐策略"
- 显示优化：用户说刷新慢/帧率低 → 读"显示优化决策"
- 性能优化：用户说"极致性能"/太慢 → 读"性能优化决策树"
- 内存问题：v2 内存不足 → 读"内存管理策略"
- 代码审查：生成代码后 → 检查"常见反模式"

---

## 输入模式决策

**触发条件 → 推荐策略：**

| 用户说 | 推荐 | 警告 |
|--------|------|------|
| "怎么读按键"/"检测触摸" | 轮询（`is_pressed()`），提及事件回调 | - |
| "响应慢"/"错过按键" | 事件回调（`event_pressed`） | 回调中禁止 `time.sleep()` |
| "多个按键"/"同时检测" | 事件回调 | 回调中禁止耗时操作 |
| 初学者 + 简单任务 | 仅轮询 | - |

**代码模板：**

```python
# 轮询
while True:
    if button_a.was_pressed():
        # 处理
    time.sleep(0.1)

# 事件回调
def on_press(pin):
    # 快速处理，不阻塞
button_a.event_pressed = on_press
```

---

## 异步推荐策略

**触发条件 → 推荐策略：**

| 用户说 | 推荐 | 条件 |
|--------|------|------|
| "网络请求阻塞"/"WiFi 卡住" | async/await | v2/v3 都支持 |
| "同时做多件事"/"边显示边接收" | 异步或协程 | - |
| 初学者 + 简单任务 | 不推荐异步 | 复杂度高 |

**代码模板：**

```python
import uasyncio as asyncio

async def fetch_data():
    # 网络操作
    await asyncio.sleep(1)

async def update_display():
    while True:
        # 更新显示
        await asyncio.sleep(0.1)

asyncio.run(asyncio.gather(fetch_data(), update_display()))
```

---

## 显示优化决策

### v2 OLED

| 用户说 | 推荐 | 何时提外部库 |
|--------|------|-------------|
| "OLED 刷新慢" | 只更新变化区域（手动缓冲区） | 不提 |
| "极致性能" + OLED | 询问是否接受外部库 → SSD1106 DPR | 用户同意后 |

### v3 LVGL

| 用户说 | 推荐 |
|--------|------|
| "LVGL 卡顿" | 只更新变化对象（`set_text()` 自动局部刷新） |
| "动画不流畅" | 调整 `event_loop(freq=50)` |
| "全屏刷新慢" | 避免 `scr.clean()`，只更新变化元素 |

**代码模板：**

```python
# v2 手动局部更新
oled.fill_rect(0, 20, 128, 10, 0)  # 只清除变化区域
oled.text(str(value), 0, 20)
oled.show()

# v3 LVGL 自动局部刷新
label.set_text(f"Count: {count}")  # 自动标记 dirty area
```

---

## 性能优化决策树

**触发条件：** 用户说"极致性能"/"优化性能"/"太慢"/"帧率低"

**行为流程：**
1. 先推荐代码优化（const、预分配、缓冲区复用）
2. 若用户仍不满意 → 用 AskUserQuestion 询问："是否接受引入外部第三方库？会增加 RAM、编译内存占用和外部依赖。"
3. 用户同意 → 根据场景推荐库 + 说明完整代价 + 建议编译为 .mpy

### MicroPython 优化技巧（优先推荐）

- `const()`：编译时常量替换
- 预分配缓冲区：避免运行时分配
- `@micropython.native`：native 编译加速
- `@micropython.viper`：更激进，需类型提示
- 缓存对象引用：避免重复查找
- 主动 `gc.collect()`

### 外部库推荐（用户同意后）

| 库 | 场景 | 收益 | 代价 |
|----|------|------|------|
| SSD1106 DPR | v2 静态内容多、频繁局部更新 | 差分页刷新 | +1KB RAM + 编译内存 + 外部依赖 |
| devlib | v2 大量文本显示、频繁刷新 | native 加速 + I2C 超频 | 替换标准库 + 编译内存 + 外部依赖 |

### 安装建议（必须告知）

1. 确定板子的 MicroPython 版本和架构：
```python
# 在板子上运行
import sys
sys_mpy = sys.implementation.mpy
arch = [None,'x86','x64','armv6','armv6m','armv7m','armv7em','armv7emsp','armv7emdp','xtensa','xtensawin'][sys_mpy >> 10]
print('版本:', sys_mpy & 0xff)
print('架构:', arch if arch else '无')
```

2. 安装对应版本的 mpy-cross（v2 是 v5，v3 是 v6）：
```bash
# AI 先探测包管理器（uv/poetry/conda/pip），再选择安装命令
# v2 (MicroPython 1.12)
pip install mpy-cross-v5

# v3 (MicroPython 1.24.1)
pip install mpy-cross-v6
```

3. 编译为 .mpy：
```bash
# v2 典型架构 xtensawin
mpy-cross-v5 -march=xtensawin library.py

# v3 典型架构 xtensawin
mpy-cross-v6 -march=xtensawin library.py
```

4. 将 .mpy 放入板子 /lib 目录

**详细说明：**
- SSD1106 DPR：见 `v2.md` OLED 部分
- devlib：见 `v2.md` OLED 部分

---

## 内存管理策略

### v2 特别注意（仅 ~120KB RAM）

| 用户说 | 推荐 |
|--------|------|
| "内存不足"/"MemoryError" | 预分配 + 分块读取 + 主动 gc.collect() |
| 使用大字符串 | 用 `'%s' % x` 或 `.format()`，不用 f-string（v2 不支持） |
| 使用大列表 | 改用 `array` 或生成器 |

### 通用技巧

- 预分配大对象（初始化时创建）
- 用 `readinto()` 而非创建新缓冲区
- 主动 `gc.collect()`（非关键时刻）
- 设置自适应阈值：`gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())`

**代码模板：**

```python
# v2 避免大字符串拼接
s = "Value: %d" % value  # ✅
s = f"Value: {value}"    # ❌ v2 不支持

# 预分配缓冲区
buf = bytearray(1024)
file.readinto(buf)  # ✅ 复用缓冲区
data = file.read()  # ❌ 每次新分配
```

---

## 常见反模式（代码审查）

**生成代码后自动检查：**

| 反模式 | 检测规则 | 警告 |
|--------|---------|------|
| 回调中 `time.sleep()` | `event_pressed` 函数内有 `sleep` | "回调中禁止阻塞，移到主循环或用异步" |
| 主循环长时间 sleep | `while True` 内 `sleep(>1)` | "用异步或降低 sleep 时间" |
| v2 OLED 频繁全屏刷新 | 循环内 `oled.fill()` + `show()` | "只更新变化区域" |
| v3 LVGL 频繁 `clean()` | 循环内 `scr.clean()` | "只更新变化对象" |
| v2 使用 f-string | 代码含 `f"..."` | "v2 不支持，改用 '%s' % x" |
| 未主动 gc | 长时间运行无 `gc.collect()` | "v2 内存紧张，主动回收" |

---

## 依赖安装规则

**行为：** 安装 Python 依赖前，先探测包管理器。

**探测顺序：**
1. 检查 `uv.lock` / `pyproject.toml` (uv) → `uv pip install`
2. 检查 `poetry.lock` (poetry) → `poetry add`
3. 检查 `conda` 环境 → `conda install`
4. 默认 → `pip install`

**示例：**

```bash
# ❌ 错误：直接 pip install
pip install mpy-cross-v5

# ✅ 正确：先探测
# 若检测到 uv
uv pip install mpy-cross-v5
```
