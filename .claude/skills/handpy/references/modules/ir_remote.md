# 红外遥控 ir_remote

`ir_remote.py` 预置于 v2 用户文件系统。v3 通过 parrot 扩展板使用红外（见 `./parrot.md`）。

## 接收

```python
from ir_remote import IRReceiver

def on_receive(data):
    print("received:", data)

ir = IRReceiver(pin=15)
ir.set_callback(on_receive)
ir.daemon()   # 启动后台线程
```

## 发送

```python
from ir_remote import IRSender

ir_tx = IRSender(pin=14)
ir_tx.send(0xFFA25D)   # 发送 NEC 编码的十六进制命令
```

## API

| 类/方法 | 说明 |
|---------|------|
| `IRReceiver(pin)` | 红外接收器 |
| `.set_callback(f)` | 设置接收回调 f(data) |
| `.daemon()` | 启动后台守护线程 |
| `IRSender(pin)` | 红外发送器 |
| `.send(cmd)` | 发送十六进制命令 |
| `IRSender.coding(cmd)` | 编码命令为脉冲列表（静态方法） |
