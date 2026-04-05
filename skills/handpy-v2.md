# HandPy v2 (ESP32) 硬件参考

## 硬件规格

| 项目 | 参数 |
|------|------|
| MCU | ESP32，240MHz |
| Flash | 4MB，无 PSRAM |
| MicroPython | 1.12.0 |
| 构建系统 | Makefile |
| 用户文件系统 | SPIFFS（较小） |
| 可用 RAM | 约 120KB，避免大字符串拼接/大列表/深层递归；分块读文件 |
| f-string | ❌ 不支持，用 `'%s' % x` 或 `.format()` |

## 引脚分配

| 外设 | 引脚 |
|------|------|
| I2C SCL | Pin(22) / P19 |
| I2C SDA | Pin(23) / P20 |
| RGB LED | Pin 17，3个 |
| 光传感器 | ADC Pin 39 |
| 声音传感器 | ADC Pin 36 |
| Button A | Pin 0 |
| Button B | Pin 2 |
| Touchpad P/Y/T/H/O/N | Pin 27/14/12/13/15/4 |

## 板载传感器

| 传感器 | 型号 | I2C 地址 |
|--------|------|----------|
| OLED | SSD1106 128×64 | 0x3C |
| 环境传感器 | BME280（温湿压） | 0x77 |
| 加速度计 | MSA300 或 QMI8658（自适应） | 0x26 / 0x6B |
| 磁力计 | MMC5983MA 或 MMC5603NJ | 0x30 |

---

## OLED

缓冲区：`oled.buffer`（bytearray，1024 bytes，MONO_VLSB，8页×128字节/页）

```python
oled.fill(0)
oled.DispChar("你好", 0, 0)   # 支持中文
oled.show()

# DispChar 参数
# mode: TextMode.normal / TextMode.rev / TextMode.trans / TextMode.xor
oled.DispChar(s, x, y, mode=TextMode.normal, auto_return=False)

oled.pixel(x, y, c)
oled.line(x1, y1, x2, y2, c)
oled.rect(x, y, w, h, c)
oled.fill_rect(x, y, w, h, c)
oled.text(s, x, y, c)      # 内置 8x8 ASCII 字体
oled.bitmap(x, y, bitmap, w, h, c)
oled.scroll(dx, dy)
oled.invert(v)
oled.contrast(c)            # 0~255
```

### 自定义字体

```python
oled.DispChar_font(s, x, y, font)
# 字体从 Flash 0x400000 读取，预置 gb2312_font.txt
```

---

## BME280

```python
bme280.temperature()   # °C
bme280.pressure()      # hPa
bme280.humidity()      # %
```

---

## 加速度计

MSA300 专有事件检测（QMI8658 无此功能）：

```python
accelerometer.set_tap_threshold(threshold)
accelerometer.set_freefall_threshold(threshold)
```

---

## 预置用户文件系统

**Python 模块：** hcsr04.py、ir_remote.py、Servo.py、siot.py、xunfei.py、smartcamera.py、smartcamera_k230.py、smartcamera_new.py、microbit.py、Obloq.py、blynklib.py、umail.py、xgo.py、yeelight.py

**图片资源：** face/（.pbm，可直接用 `oled.bitmap` 显示）、dog/

**AI / BLE / 其他：** lib/k210/、lib/k210_ai/、lib/k230_ai/、mpython_ble/、uwebsockets/、gb2312_font.txt

---

## 扩展板

| 模块 | 说明 | 详细文档 |
|------|------|----------|
| parrot.py | 掌控拓展板（电机/红外/TTS） | `./modules/parrot.md` |
| bluebit.py | 蓝比特传感器套件 | `./modules/bluebit.md` |
| educore/ | 教育核心板（需额外硬件） | — |

---

## 参考

- 官方文档：https://mPython.readthedocs.io
- 源码：https://raw.githubusercontent.com/labplus-cn/mpython/master/port/boards/mpython/modules/mpython.py
