# 部署到板子：handpy_tool.py put board/screen_server_v3.py :screen_server_v3.py
# 在主程序中：import screen_server_v3
# 注意：LVGL 非线程安全，dump 在主线程通过标志位触发
import socket, json, _thread
import lvgl as lv

_request = False
_result = None

def _dump(obj):
    r = {'type': str(type(obj)), 'x': obj.get_x(), 'y': obj.get_y(),
         'w': obj.get_width(), 'h': obj.get_height()}
    try: r['text'] = obj.get_text()
    except: pass
    ch = [_dump(obj.get_child(i)) for i in range(obj.get_child_cnt())]
    if ch: r['children'] = ch
    return r

def tick():
    """在主循环或 LVGL timer 中调用"""
    global _request, _result
    if _request:
        _result = json.dumps(_dump(lv.scr_act()))
        _request = False

def _serve():
    global _request, _result
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 8765))
    s.listen(1)
    while True:
        conn, _ = s.accept()
        try:
            _request = True
            while _request:
                pass
            conn.send(_result.encode())
        finally:
            conn.close()

_thread.start_new_thread(_serve, ())
