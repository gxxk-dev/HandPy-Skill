# bluebit 模块

`bluebit.py` 在 `v2` / `v3` 固件中都存在，提供大量传感器、显示和扩展模块驱动。

```python
from bluebit import SHT20, Ultrasonic, AmbientLight, Color

# 温湿度
sht = SHT20(i2c)
sht.temperature()
sht.humidity()

# 超声波
us = Ultrasonic(i2c)
us.distance()

# 光线
al = AmbientLight(i2c)
al.getLight()

# 颜色
color = Color(i2c)
color.getRGB()
color.getHSV()
```

## 常用模块

| 类名 | 常用方法 | 说明 |
|------|----------|------|
| `Thermistor` / `NTC` | `getTemper()` | 热敏电阻温度 |
| `LM35` | `getTemper()` | LM35 温度，`v2` 源码可见 |
| `joyButton` | `getVal()` | 四按键模块，返回 `'A'/'B'/'C'/'D'/None`，`v2` 源码可见 |
| `SHT20` | `temperature()` / `humidity()` | 温湿度 |
| `Color` | `getRGB()` / `getHSV()` | RGB / HSV 颜色识别 |
| `AmbientLight` | `getLight()` | 数字光线，返回 lux |
| `Ultrasonic` | `distance()` | 超声波测距，单位 cm |
| `SEGdisplay` | `numbers(x)` / `Clear()` | 4 位数码管 |
| `Matrix` | `bitmap()` / `show()` / `fill()` | 8x8 LED 点阵 |
| `LCD1602` | `Print()` / `Clear()` / `setCursor()` | 1602 字符 LCD，`v2` 源码可见 |

## 版本差异

- `v2` 的 `bluebit.py` 能力更多，源码里还能看到：
  - `LM35`
  - `joyButton` / `joyButton1`
  - `LCD1602`
  - `MIDI`
  - `MP3` / `MP3_`
  - `OLEDBit`
  - `IRRecv` / `IRTrans`
  - `Rfid` / `Rfid_Edu`
- `v3` 的 `bluebit.py` 保留了很多核心 I2C 模块，但模块面和 `v2` 不完全相同。
- 如果任务依赖 `LM35`、`joyButton`、`LCD1602`、`OLEDBit` 等老接口，优先按 `v2` 处理，不要默认它们在 `v3` 也存在。

## 可直接复用的最小示例

```python
from bluebit import SHT20, AmbientLight, Ultrasonic
from mpython import i2c

sht = SHT20(i2c)
print(sht.temperature(), sht.humidity())

light = AmbientLight(i2c)
print(light.getLight())

sonar = Ultrasonic(i2c)
print(sonar.distance())
```

如果任务依赖这里未列出的冷门 `bluebit` 能力，不要假设接口存在；优先说明当前文件只覆盖常用类，再按版本单独确认。
