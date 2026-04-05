# 掌控拓展板 parrot

`parrot.py` 预置于 v2 用户文件系统，也冻结于 v3 固件。

```python
import parrot

# 电机控制（速度 -100~100，负值反转）
parrot.set_speed(parrot.MOTOR_1, 80)
parrot.set_speed(parrot.MOTOR_2, -50)
parrot.get_speed(parrot.MOTOR_1)

# LED
parrot.led_on(1, brightness=50)   # 亮度 0~100
parrot.led_off(1)

# 电池电压（mV）
parrot.get_battery_level()

# 红外发送
ir_code = parrot.IR_encode()
ir = parrot.IR()
buff = ir_code.encode_nec(address=1, command=85)
ir.send(buff, repeat_en=1)
ir.stop_send()

# 红外学习
ir.learn(wait=True)   # 5秒内按住遥控器按键
data = ir.get_learn_data()
ir.send(data)
```

## 常量

```python
parrot.MOTOR_1   # 0x01
parrot.MOTOR_2   # 0x02
```

官方文档（v2）：https://mPython.readthedocs.io
官方文档（v3）：https://mpython-esp32s3-doc.readthedocs.io/zh-cn/latest/
