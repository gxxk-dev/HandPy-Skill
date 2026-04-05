# HandPy WiFi Socket Server
# 部署：handpy_tool.py install
# v2/v3 通用，MicroPython 1.12+ 兼容（无 f-string）

import socket
import struct
import _thread
import time
try:
    import json
except ImportError:
    import ujson as json

# 协议常量
CMD_EXEC = 0x01
CMD_PUT = 0x02
CMD_GET = 0x03
CMD_LS = 0x04
CMD_SCREEN = 0x05
CMD_PRESS = 0x06

PORT = 9595

# v3 LVGL 线程安全
_screen_req = False
_screen_result = None


def _log(msg):
    """日志输出到串口"""
    print('[handpy_server][%d] %s' % (time.ticks_ms(), msg))


def _send_response(conn, status, data):
    """发送响应：[1B status][4B len][data]"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    hdr = struct.pack('>BI', status, len(data))
    conn.sendall(hdr + data)


def _handle_exec(payload):
    """EXEC: 执行代码，捕获 stdout，使用隔离命名空间"""
    code = payload.decode('utf-8')
    try:
        # 捕获 stdout
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # 使用隔离的命名空间，设置 __name__ 为 '__main__'
            namespace = {'__name__': '__main__', '__builtins__': __builtins__}
            exec(code, namespace)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # 返回捕获的输出，如果为空则返回 OK
        return 0, output.encode('utf-8') if output else b'OK'
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _handle_put(payload):
    """PUT: 上传文件 [2B path_len][path][content]"""
    path_len = struct.unpack('>H', payload[:2])[0]
    path = payload[2:2+path_len].decode('utf-8')
    content = payload[2+path_len:]
    try:
        with open(path, 'wb') as f:
            f.write(content)
        return 0, b'OK'
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _handle_get(payload):
    """GET: 下载文件"""
    path = payload.decode('utf-8')
    try:
        with open(path, 'rb') as f:
            return 0, f.read()
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _handle_ls(payload):
    """LS: 列出目录"""
    import uos
    path = payload.decode('utf-8') if payload else '/'
    try:
        items = uos.listdir(path)
        return 0, '\n'.join(items).encode('utf-8')
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _handle_screen(payload):
    """SCREEN: 读取屏幕 [1B version]"""
    version = payload[0]
    try:
        if version == 0:  # v2
            import ubinascii
            from mpython import oled
            data = ubinascii.b2a_base64(bytes(oled.buffer))
            return 0, data
        else:  # v3
            global _screen_req, _screen_result
            _screen_req = True
            _screen_result = None
            # 轮询等待主线程执行 dump
            timeout = 50  # 5 秒
            while _screen_req and timeout > 0:
                time.sleep_ms(100)
                timeout -= 1
            if _screen_result is None:
                return 1, b'Timeout: call handpy_server.tick() in main loop'
            # 检查是否是错误信息
            if _screen_result.startswith('Error: '):
                return 1, _screen_result.encode('utf-8')
            return 0, _screen_result.encode('utf-8')
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _handle_press(payload):
    """PRESS: 模拟按键/触摸 [1B type][1B name_len][name][2B hold_ms]"""
    type_byte = payload[0]
    name_len = payload[1]
    name = payload[2:2+name_len].decode('utf-8')
    hold_ms = struct.unpack('>H', payload[2+name_len:4+name_len])[0]

    try:
        if type_byte == 0:  # 按键
            _press_button(name, hold_ms)
        else:  # 触摸
            _press_touch(name, hold_ms)
        return 0, b'OK'
    except Exception as e:
        return 1, str(e).encode('utf-8')


def _press_button(name, hold_ms):
    """模拟按键"""
    from mpython import button_a, button_b
    from micropython import schedule

    btn = button_a if name == 'A' else button_b

    class _FakePin:
        def value(self): return 0
        def irq(self, *a, **kw): pass

    orig = btn._Button__pin
    btn._Button__pin = _FakePin()
    btn._Button__was_pressed = True
    btn._Button__pressed_count = min(btn._Button__pressed_count + 1, 100)
    if btn.event_pressed:
        schedule(btn.event_pressed, btn._Button__pin)
    time.sleep_ms(hold_ms)
    btn._Button__pin = orig
    if btn.event_released:
        schedule(btn.event_released, orig)


def _press_touch(name, hold_ms):
    """模拟触摸"""
    from mpython import touchPad_P, touchPad_Y, touchPad_T, touchPad_H, touchPad_O, touchPad_N

    touch_map = {
        'P': touchPad_P, 'Y': touchPad_Y, 'T': touchPad_T,
        'H': touchPad_H, 'O': touchPad_O, 'N': touchPad_N,
    }
    touch = touch_map[name]

    touch._Touch__value = 1
    touch._Touch__was_pressed = True
    touch._Touch__pressed_count = min(touch._Touch__pressed_count + 1, 100)
    if touch.event_pressed:
        touch.event_pressed(1)
    time.sleep_ms(hold_ms)
    touch._Touch__value = 0
    if touch.event_released:
        touch.event_released(0)


def _handle_client(conn, addr):
    """处理单个客户端连接"""
    try:
        # 读取请求头 [1B cmd][4B len]，循环累积直到读满 5 字节
        hdr = b''
        while len(hdr) < 5:
            chunk = conn.recv(5 - len(hdr))
            if not chunk:
                return
            hdr += chunk

        cmd, length = struct.unpack('>BI', hdr)

        # 读取 payload，必须读满，否则视为协议错误
        payload = b''
        while len(payload) < length:
            chunk = conn.recv(length - len(payload))
            if not chunk:
                _log('Error: Incomplete payload (expected %d, got %d)' % (length, len(payload)))
                _send_response(conn, 1, b'Incomplete payload')
                return
            payload += chunk

        _log('Client %s, CMD=0x%02x' % (addr[0], cmd))

        # 分发命令
        handlers = {
            CMD_EXEC: _handle_exec,
            CMD_PUT: _handle_put,
            CMD_GET: _handle_get,
            CMD_LS: _handle_ls,
            CMD_SCREEN: _handle_screen,
            CMD_PRESS: _handle_press,
        }

        if cmd in handlers:
            status, data = handlers[cmd](payload)
            _send_response(conn, status, data)
        else:
            _send_response(conn, 1, b'Unknown command')
    except Exception as e:
        _log('Error: %s' % str(e))
        try:
            _send_response(conn, 1, str(e).encode('utf-8'))
        except:
            pass
    finally:
        conn.close()


def _connect_wifi():
    """连接 WiFi，返回 IP 或 None"""
    import network
    import re

    # 读取 boot.py 中的 WIFI_CREDS，仅解析标记块
    try:
        with open('boot.py', 'r') as f:
            boot_code = f.read()
        # 提取标记块中的 WIFI_CREDS
        match = re.search(r'# HANDPY_SERVER_BEGIN.*?WIFI_CREDS\s*=\s*(\[.*?\]).*?# HANDPY_SERVER_END',
                          boot_code, re.DOTALL)
        if not match:
            _log('WIFI_CREDS not found in boot.py')
            return None

        creds_str = match.group(1)
        # 安全解析：wifi add 写入的是合法 JSON，直接解析
        try:
            import json
        except ImportError:
            import ujson as json
        creds = json.loads(creds_str)
    except Exception as e:
        _log('Failed to read WIFI_CREDS: %s' % str(e))
        return None

    if not creds:
        _log('WIFI_CREDS is empty')
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    for cred in creds:
        ssid = cred['ssid']
        pwd = cred['pwd']
        _log('Trying SSID: %s' % ssid)

        wlan.connect(ssid, pwd)

        # 等待连接，最多 10 秒
        for _ in range(100):
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                _log('Connected, IP: %s' % ip)
                return ip
            time.sleep_ms(100)

        _log('Failed to connect to %s' % ssid)

    return None


def _server_thread():
    """后台服务线程"""
    _log('Starting...')

    # 连接 WiFi
    ip = _connect_wifi()
    if ip is None:
        _log('No WiFi connection, exiting')
        return

    # 绑定端口
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PORT))
    s.listen(1)
    _log('Listening on port %d' % PORT)

    # accept 循环
    while True:
        try:
            conn, addr = s.accept()
            _handle_client(conn, addr)
        except Exception as e:
            _log('Accept error: %s' % str(e))


def tick():
    """v3 LVGL 线程安全：主线程调用此函数执行屏幕 dump"""
    global _screen_req, _screen_result
    if _screen_req:
        try:
            import lv_displayer
            import lvgl as lv

            def _dump(o):
                r = {
                    'type': str(type(o)),
                    'x': o.get_x(),
                    'y': o.get_y(),
                    'w': o.get_width(),
                    'h': o.get_height()
                }
                try:
                    r['text'] = o.get_text()
                except:
                    pass
                ch = [_dump(o.get_child(i)) for i in range(o.get_child_cnt())]
                if ch:
                    r['children'] = ch
                return r

            _screen_result = json.dumps(_dump(lv.screen_active()))
        except Exception as e:
            _screen_result = 'Error: %s' % str(e)
        finally:
            _screen_req = False


# 启动后台线程
_thread.start_new_thread(_server_thread, ())
