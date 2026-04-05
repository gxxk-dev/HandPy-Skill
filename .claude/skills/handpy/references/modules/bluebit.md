# 蓝比特 bluebit

`bluebit.py` 预置于 v2 用户文件系统，提供多种传感器模块驱动。

```python
from bluebit import SHT20, Ultrasonic, AmbientLight, joyButton

# 温湿度
sht = SHT20(i2c)
sht.temperature()
sht.humidity()

# 超声波
us = Ultrasonic(i2c)
us.distance()

# 光线
al = AmbientLight(i2c)
al.read()

# 四按键
joy = joyButton(i2c)
joy.btnA()   # 返回 True/False
joy.btnB()
joy.btnC()
joy.btnD()
```

## 支持的模块

| 类名 | 功能 |
|------|------|
| `Thermistor` / `NTC` | 热敏电阻温度 |
| `LM35` | LM35 温度传感器 |
| `joyButton` | 四按键模块 |
| `SHT20` | 温湿度 |
| `Color` | RGB 颜色识别 |
| `AmbientLight` | 光照强度 |
| `Ultrasonic` | 超声波测距 |
| `SEGdisplay` | 7段数码管 |
| `Matrix` | LED 矩阵（HT16K33） |
| `LCD1602` | 16×2 字符 LCD |
| `Barometric` | 气压（SPL06） |
| `Gesture` | 手势识别（APDS9960） |
| `max30102` | 心率/血氧 |

官方文档（v2）：https://mPython.readthedocs.io
