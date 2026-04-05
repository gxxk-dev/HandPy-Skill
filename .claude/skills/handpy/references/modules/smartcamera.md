# AI 摄像头 smartcamera

`smartcamera_k230.py`（K230）和 `smartcamera_new.py`（K210）预置于 v2/v3 用户文件系统，通过 UART 与外接 AI 摄像头模块通信。

## K230

```python
from smartcamera_k230 import SmartCameraK230
from mpython import Pin

cam = SmartCameraK230(tx=Pin.P1, rx=Pin.P0)
cam.wait_for_ai_init()   # 等待 AI 模块初始化完成
```

## K210

```python
from smartcamera_new import SmartCamera

cam = SmartCamera(tx=Pin.P1, rx=Pin.P0)
cam.wait_for_ai_init()
```

> 两者均需外接对应的 AI 摄像头硬件模块，通过 UART 串口通信。
> 详细 AI 功能 API 见 `lib/k230_ai/` 或 `lib/k210_ai/` 目录。
