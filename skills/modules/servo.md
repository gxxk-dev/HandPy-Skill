# 舵机 Servo

## v2

`Servo.py` 预置于 v2 用户文件系统，是对内置 `servo` 模块的简单包装。

```python
from Servo import Servo

s = Servo(pin=15)
s.angle(90)    # 设置角度 0~180
```

## v3

`servo.py` 冻结于 v3 固件，完整 PWM 实现，参数更多。

```python
from servo import Servo

s = Servo(pin=15, freq=50, angle=0, min_us=750, max_us=2250, actuation_range=180)
s.write_angle(90)
s.freq(50)
```

## API 对比

| 方法 | v2 | v3 |
|------|----|----|
| 构造函数 | `Servo(pin)` | `Servo(pin, freq, angle, min_us, max_us, actuation_range)` |
| 设置角度 | `angle(deg)` | `write_angle(deg)` |
| 设置频率 | — | `freq(hz)` |

官方文档（v2）：https://mPython.readthedocs.io
官方文档（v3）：https://mpython-esp32s3-doc.readthedocs.io/zh-cn/latest/
