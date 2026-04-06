---
name: handpy
description: Use for HandPy / mPython / 掌控板 coding and board-control tasks, including v2/v3 APIs, OLED/LCD/LVGL, built-in sensors, bundled modules such as SIoT, HCSR04, servo, parrot, bluebit, smartcamera, BLE, and xunfei, plus the optional `handpy-tool` utility for running code, transferring files, reading the screen, simulating button/touch input, or flashing firmware. 适用于 HandPy v2/v3 开发、调试、模块使用和可选真机控制；不适用于没有 HandPy API 的通用 ESP32 板卡。
---

# HandPy

用于 HandPy 专属 MicroPython 开发与可选真机控制。

## 读取顺序

- 先读 [references/common.md](references/common.md)，获取通用 API、Python 兼容性和模块索引。
- 当任务明确是 `v2`，或涉及板载 `oled` / `oled.DispChar()` / 单色 OLED 屏时，再读 [references/v2.md](references/v2.md)。
- 当任务明确是 `v3`，或涉及 LCD、彩色屏幕、LVGL、`lv_gui.py`、`lv_displayer`、ESP32-S3 时，再读 [references/v3.md](references/v3.md)。
- 只有在任务需要主机侧与板子交互时，才读 [references/tool.md](references/tool.md)，例如执行代码、传文件、读屏、模拟按键/触摸、刷固件。
- 若用户明确要求"性能优化"/"极致性能"/"帧率低"/"太慢"，读取 [references/patterns.md](references/patterns.md)（编程模式与优化指南）。

## 版本判断

- 若请求没有说明板型，但答案会因版本而变，先询问用户是 `v2` 还是 `v3`。
- 若请求已明显指向某版本，则直接按该版本回答，不要机械追问。
- 常见信号：
  - 板载 `oled`、`oled.DispChar()`、`oled.bitmap()`、单色 OLED 屏，通常是 `v2`
  - LCD、彩色屏幕、LVGL、`lv_gui.py`、`lv_displayer`、ESP32-S3，通常是 `v3`
  - `WiFi` / AP 模式、BLE、光照/声音/加速度计/磁力计、`smartcamera_k230.py` / `smartcamera_new.py` 不能单独作为版本信号

## 模块 references

- [references/modules/siot.md](references/modules/siot.md): SIoT / MQTT
- [references/modules/hcsr04.md](references/modules/hcsr04.md): 超声波测距
- [references/modules/ir_remote.md](references/modules/ir_remote.md): 红外收发
- [references/modules/smartcamera.md](references/modules/smartcamera.md): K210 / K230 AI 摄像头
- [references/modules/servo.md](references/modules/servo.md): 舵机
- [references/modules/parrot.md](references/modules/parrot.md): 掌控拓展板 / 电机 / 扩展板红外
- [references/modules/bluebit.md](references/modules/bluebit.md): `bluebit` 扩展模块
- [references/modules/xunfei.md](references/modules/xunfei.md): 讯飞语音
- [references/modules/mpython_ble.md](references/modules/mpython_ble.md): BLE
- [references/modules/lv_gui.md](references/modules/lv_gui.md): `v3` 的 `lv_gui.py` 与 LVGL 页面封装
- [references/modules/images.md](references/modules/images.md): 预置图片资源

只在请求明确提到某模块，或实现明显依赖该模块时读取对应文件。

## 输出要求

- 优先使用 HandPy / mPython 原生 API，给出能直接在板子上运行的示例。
- 需要体现版本差异时，直接在答案里标注 `v2` / `v3`，不要默认把两套方案都展开。
- `handpy-tool` 是可选增强，不要把它当作所有任务的前置条件。
