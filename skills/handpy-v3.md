# HandPy v3 (ESP32-S3) 硬件参考

## 硬件规格

| 项目 | 参数 |
|------|------|
| MCU | ESP32-S3，240MHz，PSRAM |
| Flash | 16MB |
| MicroPython | 1.24.1 |
| 构建系统 | CMake |
| 用户文件系统 | SPIFFS 2MB（0x6F0000–0x8F0000） |
| 语音数据分区 | 3.9MB（0x8F0000–0xCBD000） |
| f-string | ✅ 支持 |

## 引脚分配

| 外设 | 引脚 |
|------|------|
| I2C SCL | Pin(35) |
| I2C SDA | Pin(34) |
| RGB LED | Pin 8，3个 |
| 光传感器 | LTR-308ALS，I2C 0x53 |
| 声音传感器 | ADC Pin 6 |
| Button A | Pin 0 |
| Button B | Pin 46 |
| Touchpad P/Y/T/H/O/N | Pin 9/10/11/12/13/14 |
| 加速度计 INT | Pin 45 |

## 板载传感器

| 传感器 | 型号 | 地址 |
|--------|------|------|
| 显示屏 | LCD 320×172，JD9853，SPI | — |
| 光传感器 | LTR-308ALS（自动检测） | I2C 0x53 |
| 加速度计 | QMI8658C（固定） | I2C 0x6B |
| 磁力计 | MMC5603NJ（自动检测） | I2C 0x30 |
| 音频编解码器 | ES8388 | I2C 0x10 |

## 音频系统

ES8388，I2S，双麦克风阵列 + 扬声器，16kHz/16bit 立体声。

| 信号 | 引脚 |
|------|------|
| MCLK | 39 |
| SCLK | 41 |
| LRCK | 42 |
| DOUT（扬声器） | 38 |
| SDIN（麦克风） | 40 |

---

## LCD / LVGL

启动时 `_boot.py` 自动调用 `lcd.draw_logo()`，用户代码直接使用 LVGL。

```python
import lvgl as lv
from lv_utils import event_loop

el = event_loop()   # 默认 25Hz 刷新

scr = lv.scr_act()
label = lv.label(scr)
label.set_text("Hello HandPy")
label.align(lv.ALIGN.CENTER, 0, 0)
```

### 内置字体

```python
lv.font_montserrat_16    # Montserrat 系列，8~48px
lv.font_simsun_14_cjk    # SimSun CJK 14px
lv.font_simsun_16_cjk    # SimSun CJK 16px
# 思源黑体 24px 也已内置
```

### 动态加载字体

```python
font = lv.binfont_create("/font/myfont.bin")
```

详细 GUI 用法：`./modules/lv_gui.md`

---

## 光传感器

```python
light.read()   # 返回光照值（lux）
```

---

## RFID（外接 I2C 模块，非板载）

```python
from mfrc import Rfid
rfid = Rfid(i2c, i2c_addr=47)   # 0x2F
```

---

## 预置用户文件系统

**Python 模块：** smartcamera_k230.py、smartcamera_new.py、lv_gui.py、utils.py

**字体：** font/digital_dot_matrix.py（16×32 点阵字体）

**图片资源：** images/B&W/（54张 PNG）、images/Color/（56张 PNG）

**AI / BLE / 其他：** lib/k210_ai/、lib/k230_ai/、mpython_ble/、urequests/、gb2312_font.txt

---

## 参考

- 官方文档：https://mpython-esp32s3-doc.readthedocs.io/zh-cn/latest/
- 源码：https://raw.githubusercontent.com/labplus-cn/mpython_esp32s3/dev/port/boards/mpython_pro/modules/mpython.py
