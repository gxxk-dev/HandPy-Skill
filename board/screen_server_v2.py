# 部署到板子：handpy_tool.py put board/screen_server_v2.py :screen_server_v2.py
# 在主程序中：import screen_server_v2
import socket, ubinascii, _thread
from mpython import oled

def _serve():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 8765))
    s.listen(1)
    while True:
        conn, _ = s.accept()
        try:
            conn.send(ubinascii.b2a_base64(bytes(oled.buffer)))
        finally:
            conn.close()

_thread.start_new_thread(_serve, ())
