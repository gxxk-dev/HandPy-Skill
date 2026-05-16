# BLE 蓝牙 mpython_ble

`mpython_ble/` 预置于 v2/v3 用户文件系统，提供 BLE 外设、中心设备、串口透传、HID 和 iBeacon。

```python
from mpython_ble.application.peripheral import Peripheral
from mpython_ble.application.centeral import Centeral   # 源码类名就是 Centeral
from mpython_ble.application.uart import BLEUART
from mpython_ble.application.hid import HID
from mpython_ble.application.beacon import iBeacon
```

## 常用高层封装

### BLEUART 串口透传

```python
from mpython_ble.application.uart import BLEUART
import time

uart = BLEUART(name=b'handpy-uart', role=BLEUART.SLAVE)

def on_rx():
    print(uart.read())

uart.irq(on_rx)

while True:
    if uart.is_connected():
        uart.write(b'hello')
    time.sleep_ms(500)
```

常用 API：

| 方法 | 说明 |
|------|------|
| `BLEUART(name=b'ble_uart', appearance=0, rxbuf=100, role=0, slave_mac=None)` | 初始化；`role=BLEUART.SLAVE` 为外设，`role=BLEUART.MASTER` 为中心 |
| `is_connected()` | 是否已连接 |
| `irq(handler)` | 注册接收回调 |
| `any()` | 当前接收缓冲区字节数 |
| `read(size=None)` | 读取缓冲区 |
| `write(data)` | 发送字节数据 |
| `close()` | 断开连接 |

### HID

```python
from mpython_ble.application.hid import HID

hid = HID(name=b'handpy-hid')
hid.advertise(True)

# 鼠标
hid.mouse_move(20, 0)
hid.mouse_click(1)

# 键盘
hid.keyboard_send(4)   # keycode 取自 hidcode.py
```

常用 API：

| 方法 | 说明 |
|------|------|
| `HID(name=b'mpy_hid', battery_level=100)` | 初始化 HID 设备 |
| `advertise(toggle=True)` | 开始/停止广播 |
| `disconnect()` | 断开连接 |
| `mouse_click(buttons)` / `mouse_press(buttons)` / `mouse_release(buttons)` | 鼠标按键 |
| `mouse_move(x=0, y=0, wheel=0)` | 鼠标移动/滚轮 |
| `keyboard_press(*keycodes)` / `keyboard_release(*keycodes)` / `keyboard_send(*keycodes)` | 键盘发送 |
| `consumer_send(code)` | 发送媒体键等 consumer 控制码 |

### iBeacon

```python
from mpython_ble.application.beacon import iBeacon

beacon = iBeacon(
    proximity_uuid='E2C56DB5-DFFB-48D2-B060-D0F5A71096E0',
    major=1,
    minor=1
)
beacon.advertise(True)
```

## 低层接口

- `Peripheral`：自定义 GATT 外设
- `Centeral`：中心设备，支持 `connect()`、`characteristic_read()`、`characteristic_write()`、`notify_callback()`

如果只是做板间透传、键鼠模拟或 beacon，优先使用上面的高层封装，不要直接从 `Peripheral` 开始搭。

## 版本说明

- v2 和 v3 的 `BLEUART`、`Peripheral`、`HID` 主接口基本一致。
- v3 的 `beacon.py` 额外包含 `BeaconScanner` 和 `Trilateration`，可做 iBeacon 扫描与定位计算。
