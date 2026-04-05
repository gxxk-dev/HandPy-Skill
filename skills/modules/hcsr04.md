# 超声波测距 HCSR04

`hcsr04.py` 预置于 v2/v3 用户文件系统。

```python
from hcsr04 import HCSR04

sonar = HCSR04(trigger_pin=15, echo_pin=14)

dist_mm = sonar.distance_mm()   # 毫米，整数
dist_cm = sonar.distance_cm()   # 厘米，浮点数
```

## API

| 方法 | 说明 |
|------|------|
| `HCSR04(trigger_pin, echo_pin, echo_timeout_us=30000)` | 初始化 |
| `distance_mm()` | 返回距离（mm） |
| `distance_cm()` | 返回距离（cm） |
