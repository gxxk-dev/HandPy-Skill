# SIoT MQTT 客户端

SIoT 是掌控板配套的 MQTT 物联网平台，`siot.py` 预置于用户文件系统。

```python
from siot import iot

client = iot(
    client_id="my_device",
    server="192.168.1.100",   # SIoT 服务器 IP
    port=1883,
    user="siot",
    password="siot"
)
client.connect()

# 发布消息
client.publish("topic/test", "hello")

# 订阅消息
def on_message(topic, msg):
    print(topic, msg)

client.subscribe("topic/test", on_message)
client.loop()   # 启动定时器循环（非阻塞）

# 或手动轮询
client.check_msg()

# 断开
client.stop()
```

## API

| 方法 | 说明 |
|------|------|
| `connect(clean_session=True)` | 连接服务器 |
| `publish(topic, msg, retain=False, qos=0)` | 发布消息 |
| `subscribe(topic, callback)` | 订阅主题，callback(topic, msg) |
| `loop()` | 启动定时器自动轮询 |
| `check_msg()` | 手动检查一次消息 |
| `wait_msg()` | 阻塞等待一条消息 |
| `set_last_will(topic, msg)` | 设置遗嘱消息 |
| `stop()` | 断开连接 |
