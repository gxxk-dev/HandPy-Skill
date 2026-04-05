# HandPy (mPython) 通用硬件参考

> 支持版本：v2（ESP32）、v3（ESP32-S3）
> 不支持：labplus_1956、labplus_classroom_kit_II、labplus-experiment-box-2024、mpython-classroom-kit、labplus_Ledong_v2

**上位机工具**：`handpy_tool.py` 提供串口/WiFi 控制、文件传输、读屏、模拟输入等功能，详见 `./handpy-tool.md`

---

## 导入

```python
from mpython import *   # 导入所有预定义对象
```

---

## RGB LED（NeoPixel × 3）

```python
rgb[0] = (255, 0, 0)    # 设置第0个 LED 为红色
rgb[1] = (0, 255, 0)
rgb[2] = (0, 0, 255)
rgb.write()             # 刷新输出

rgb.fill((255, 255, 0)) # 全部设为同一颜色
rgb.write()

rgb.brightness(0.5)     # 设置亮度 0.0~1.0
```

---

## 按键 A/B

Button A = Pin 0（v2/v3 相同），Button B 引脚见各版本文档。

```python
# 轮询
button_a.is_pressed()       # 当前是否按下（直接读硬件）
button_a.was_pressed()      # 自上次调用后是否按过（消耗一次）
button_a.get_presses()      # 自上次调用后按下次数（消耗）

# 事件回调
def on_press(pin):
    print("pressed")

button_a.event_pressed = on_press
button_a.event_released = lambda p: print("released")
```

---

## 触摸板 P/Y/T/H/O/N

引脚见各版本文档。

```python
touchPad_P.is_pressed()     # 当前是否触摸（读缓存）
touchPad_P.was_pressed()
touchPad_P.get_presses()
touchPad_P.read()           # 读取原始电容值（越小越接近触摸）

touchPad_P.event_pressed = lambda v: print("touch P")
touchPad_P.event_released = lambda v: print("release P")

# 调整灵敏度阈值
touchPad_P.config(threshold=30000)
```

---

## 蜂鸣器 / 音乐

```python
import music

music.play(music.DADADADUM)     # 播放内置曲目
music.play(['C4:4', 'D4:4', 'E4:8'])  # 音符列表
music.pitch(440, duration=500)  # 播放指定频率（Hz），duration ms（-1 持续）
music.stop()
music.set_tempo(bpm=120, ticks=4)
```

---

## WiFi

```python
from mpython import wifi

wifi.connectWiFi('SSID', 'password')    # 连接，默认超时 10s
wifi.disconnectWiFi()

# v3 额外支持 AP 模式
wifi.enable_APWiFi('MyAP', password='12345678', channel=10)
wifi.disable_APWiFi()
```

---

## MPythonPin IO

```python
from mpython import MPythonPin, PinMode
from machine import Pin

p0 = MPythonPin(0, PinMode.IN)          # 数字输入
p0 = MPythonPin(0, PinMode.IN, pull=Pin.PULL_UP)
p0.read_digital()                        # 返回 0 或 1

p1 = MPythonPin(1, PinMode.OUT)
p1.write_digital(1)

p2 = MPythonPin(2, PinMode.PWM)
p2.write_analog(512, freq=1000)          # duty 0~1023，freq Hz

p3 = MPythonPin(3, PinMode.ANALOG)
p3.read_analog()                         # 返回 0~4095

p4 = MPythonPin(4, PinMode.OUT_DRAIN)   # 开漏输出
```

---

## 加速度计 / 陀螺仪 / 磁力计

```python
# 加速度计（单位 g）
accelerometer.get_x()
accelerometer.get_y()
accelerometer.get_z()
accelerometer.set_range(range)          # 设置量程
accelerometer.set_offset(x, y, z)      # 设置偏移
accelerometer.roll_pitch_angle()        # 返回 (roll, pitch)

# 陀螺仪（单位 °/s）
gyroscope.get_x()
gyroscope.get_y()
gyroscope.get_z()
gyroscope.set_range(range)
gyroscope.set_ODR(odr)                  # 设置输出数据率
gyroscope.set_offset(x, y, z)

# 磁力计（单位 μT）
magnetic.get_x()
magnetic.get_y()
magnetic.get_z()
magnetic.get_heading()                  # 返回方位角（0~360°）
magnetic.get_field_strength()           # 返回磁场强度
magnetic.calibrate()                    # 校准（需旋转板子）
```

---

## 声音传感器

```python
sound.read()    # 返回 0~4095，值越大声音越响
```

---

## Python 特性支持

| 特性 | v2 (MicroPython 1.12) | v3 (MicroPython 1.24.1) |
|------|----------------------|------------------------|
| f-string | ❌ | ✅ |
| match/case | ❌ | ❌ |
| 海象运算符 := | ✅ | ✅ |
| async/await | ✅ | ✅ |

v2 请用 `'Hello %s' % name` 或 `.format()` 替代 f-string。

---

## 模块索引

需要某个模块的详细说明时，读取对应文件：

| 模块 | 文件 |
|------|------|
| SIoT MQTT | `./modules/siot.md` |
| 超声波 HCSR04 | `./modules/hcsr04.md` |
| 红外遥控 | `./modules/ir_remote.md` |
| AI 摄像头 | `./modules/smartcamera.md` |
| 舵机 Servo | `./modules/servo.md` |
| 掌控拓展板 parrot | `./modules/parrot.md` |
| 蓝比特 bluebit | `./modules/bluebit.md` |
| 讯飞语音 | `./modules/xunfei.md` |
| BLE 蓝牙 | `./modules/mpython_ble.md` |
| LVGL GUI（v3） | `./modules/lv_gui.md` |
| 预置图片资源 | `./modules/images.md` |
