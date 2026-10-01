#!/usr/bin/env python3
"""HandPy (mPython) board control tool."""

import argparse
import sys
import base64
import json
from pathlib import Path
from contextlib import contextmanager

from mpremote.transport_serial import SerialTransport
from mpremote.commands import CommandError


# ── board constants ───────────────────────────────────────────────────────────

V2 = 'v2'
V3 = 'v3'
ESP32 = 'esp32'
ESP32S3 = 'esp32s3'


# ── port detection ────────────────────────────────────────────────────────────

BAD_PORT_HINTS = (
    'bluetooth',
    'incoming-port',
)


def _port_score(port):
    device = port.device or ''
    device_l = device.lower()
    desc = (port.description or '').lower()
    hwid = (port.hwid or '').lower()
    text = ' '.join((device_l, desc, hwid))

    if any(x in text for x in BAD_PORT_HINTS):
        return -1000

    s = 0
    if (
        '/ttyacm' in device_l
        or '/ttyusb' in device_l
        or '/dev/cu.usb' in device_l
    ):
        s += 100
    if device_l.startswith('com'):
        s += 10
    # On macOS both /dev/tty.usb* and /dev/cu.usb* may exist; use callout ports.
    if '/dev/tty.usb' in device_l:
        s -= 20
    if any(x in desc for x in (
        'cp210', 'ch340', 'ch910', 'ftdi', 'usb serial',
        'usb single serial', 'usb jtag/serial', 'jtag/serial',
        'cdc', 'acm',
    )):
        s += 50
    if any(x in hwid for x in ('vid:pid=1a86', 'vid:pid=10c4', 'vid:pid=0403', 'vid:pid=303a')):
        s += 30
    # Linux exposes many built-in ttyS ports; they are almost never USB boards.
    if device.startswith('/dev/ttyS'):
        s -= 100
    return s


def _select_port(ports):
    candidates = sorted(ports, key=lambda p: (-_port_score(p), p.device or ''))
    if _port_score(candidates[0]) > 0:
        return candidates[0].device
    for p in ports:
        if _port_score(p) > -1000 and not (p.device or '').startswith('/dev/ttyS'):
            return p.device
    return None


def find_port():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        raise RuntimeError("No serial port found. Use --port to specify.")
    selected = _select_port(ports)
    if selected:
        return selected
    raise RuntimeError("No serial port found. Use --port to specify.")


# ── mpremote helpers ──────────────────────────────────────────────────────────

def _enter_raw_repl(t, soft_reset, attempts=8):
    """反复尝试进入 raw REPL。

    自启脚本（boot.py/main.py 里的死循环）会持续刷提示符抢占串口，单次
    enter_raw_repl() 很难抢赢——实测需要 5～10 次重试。逐次尝试时每次都先
    Ctrl-C 打断当前程序，再请求进入。
    """
    import time
    from mpremote.transport import TransportError

    last = None
    for i in range(max(1, attempts)):
        try:
            for _ in range(3):
                t.serial.write(b"\r\x03")
                time.sleep(0.05)
            n = t.serial.inWaiting()
            while n > 0:
                t.serial.read(n)
                n = t.serial.inWaiting()
            t.enter_raw_repl(soft_reset=soft_reset, timeout_overall=1.0)
            # 抢占过程中板子可能还在吐自启脚本的输出，残留字节会让后续 exec
            # 读到 "raw REPL" 的片段（could not exec command: b'ra'）。
            # 成功后退回并刷干净，再交还给调用方。
            try:
                if t.in_raw_repl:
                    t.exit_raw_repl()
            except Exception:
                pass
            n = t.serial.inWaiting()
            while n > 0:
                t.serial.read(n)
                time.sleep(0.02)
                n = t.serial.inWaiting()
            t.enter_raw_repl(soft_reset=False, timeout_overall=2.0)
            if i:
                print(f"Entered raw REPL after {i + 1} attempt(s).", file=sys.stderr)
            return
        except TransportError as e:
            last = e
            time.sleep(0.1)
    raise last if last else TransportError("could not enter raw repl")


@contextmanager
def _transport(port, soft_reset=True, grab_attempts=8):
    import time
    from mpremote.transport import TransportError

    # RTS 复位会让 USB 重新枚举，设备节点会短暂消失；mpremote 默认 wait=0
    # 只试一次就报错，所以这里自己重试打开。
    t = None
    last = None
    for _ in range(10):
        try:
            t = SerialTransport(port, baudrate=115200, wait=1)
            break
        except TransportError as e:
            last = e
            time.sleep(0.5)
    if t is None:
        raise RuntimeError(
            "无法打开串口 %s（%s）。确认设备已连接，或板子正在重新枚举。" % (port, last)
        )
    t.use_raw_paste = False  # handpy_server socket data corrupts raw-paste handshake
    try:
        try:
            _enter_raw_repl(t, soft_reset, grab_attempts)
        except TransportError as e:
            raise RuntimeError(
                "无法进入 raw REPL（%s）。板子可能仍在启动，或 boot.py/main.py "
                "里的自启脚本正独占串口：等待几秒重试，或执行 "
                "'handpy-tool reset --grab' 复位并抢回串口。" % e
            ) from e
        if soft_reset:
            # boot.py restarts handpy_server; wait for it then flush and re-sync
            time.sleep(2.5)
            n = t.serial.inWaiting()
            while n > 0:
                t.serial.read(n)
                n = t.serial.inWaiting()
            t.serial.write(b"\x01")
            t.read_until(1, b"raw REPL; CTRL-B to exit\r\n")
        yield t
    finally:
        try:
            if t.in_raw_repl:
                t.exit_raw_repl()
        except Exception:
            pass
        t.close()


def _write_stdout_data(data):
    if not data:
        return
    if isinstance(data, str):
        data = data.encode('utf-8', errors='replace')
    sys.stdout.buffer.write(data)


def _print_stderr_data(data):
    if not data:
        return
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    else:
        data = str(data)
    print(data, file=sys.stderr, end='' if data.endswith('\n') else '\n')


def _exec_error_streams(e):
    """兼容不同 mpremote 版本，取出 (stdout bytes, stderr str)。

    新版 TransportExecError(status_code, error_output) 里 stdout 数据存放在
    status_code，错误文本在 error_output；老版本直接用 args 元组传两个值。
    """
    stdout = getattr(e, 'status_code', None)
    stderr = getattr(e, 'error_output', None)
    if stderr is None and e.args:
        stderr = e.args[-1]
    if not isinstance(stdout, (bytes, bytearray)) and len(e.args) > 1:
        stdout = e.args[0]
    if isinstance(stdout, str):
        stdout = stdout.encode('utf-8', errors='replace')
    if not isinstance(stdout, (bytes, bytearray)):
        stdout = b''
    if stderr is None:
        stderr = ''
    return bytes(stdout), str(stderr)


def _pump_stdin(t, stop_event):
    """把本地 stdin 逐字节转发给板子，让板端 input() 能拿到输入。"""
    import os
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, ValueError):
        return
    while not stop_event.is_set():
        try:
            chunk = os.read(fd, 1)
        except OSError:
            return
        if not chunk:
            return
        try:
            t.serial.write(chunk)
        except Exception:
            return


def run_streaming(t, command, timeout=None, forward_stdin=False):
    """流式执行板端代码：边跑边输出，长时脚本不会因静默超时被误杀。

    timeout=None 表示一直等到脚本自己结束；follow() 的超时是"两个字符之间"的
    静默超时，原先用 t.exec() 会在这里误判失败。
    """
    from mpremote.transport import stdout_write_bytes
    import threading

    if isinstance(command, str):
        command = command.encode('utf-8')
    t.exec_raw_no_follow(command)

    stop_event = None
    if forward_stdin:
        stop_event = threading.Event()
        threading.Thread(target=_pump_stdin, args=(t, stop_event), daemon=True).start()
    try:
        data, data_err = t.follow(timeout=timeout, data_consumer=stdout_write_bytes)
    except KeyboardInterrupt:
        # Ctrl-C 转发给板子，中断正在跑的脚本
        try:
            t.serial.write(b"\x03")
        except Exception:
            pass
        raise
    finally:
        if stop_event is not None:
            stop_event.set()

    if data_err:
        _print_stderr_data(data_err)
        sys.exit(1)
    return data


def run(args, port, capture=True, timeout=None, forward_stdin=False):
    from mpremote.transport import TransportExecError

    # strip leading 'resume' (means no soft reset)
    soft_reset = True
    while args and args[0] == 'resume':
        args = args[1:]
        soft_reset = False

    op = args[0]
    try:
        if op == 'exec':
            if capture:
                with _transport(port, soft_reset) as t:
                    out = t.exec(args[1])
                return out.decode('utf-8')
            with _transport(port, soft_reset) as t:
                run_streaming(t, args[1], timeout=timeout, forward_stdin=forward_stdin)
        elif op == 'run':
            if capture:
                with _transport(port, soft_reset) as t:
                    out = t.execfile(args[1])
                return out.decode('utf-8')
            buf = Path(args[1]).read_bytes()
            with _transport(port, soft_reset) as t:
                run_streaming(t, buf, timeout=timeout, forward_stdin=forward_stdin)
        elif op == 'cp':
            src, dst = args[1], args[2]
            with _transport(port, soft_reset) as t:
                if dst.startswith(':'):
                    data = Path(src).read_bytes()
                    t.fs_writefile(dst[1:], data)
                else:
                    data = t.fs_readfile(src[1:])
                    Path(dst).write_bytes(data)
        elif op == 'rm':
            with _transport(port, soft_reset) as t:
                t.fs_rmfile(args[1].lstrip(':'))
        else:
            raise ValueError(f"Unsupported mpremote op: {op}")
    except TransportExecError as e:
        stdout, stderr = _exec_error_streams(e)
        _write_stdout_data(stdout)
        _print_stderr_data(stderr)
        sys.exit(1)


# ── board detection ───────────────────────────────────────────────────────────

def detect_board(port=None, host=None, transport='serial'):
    """自动检测板子型号，返回 (version, chip) 元组

    通过 os.uname() 的最后一个字段判断：
    - v3: 'mpython pro with ESP32S3'
    - v2: 'mpython with ESP32'

    Returns:
        (V2, ESP32) 或 (V3, ESP32S3)
    """
    detect_code = "print(list(__import__('os').uname()))"

    if transport == 'wifi' and host:
        try:
            result = _wifi_cmd(host, 0x01, detect_code.encode('utf-8'))
            uname_str = result.decode('utf-8').strip()
        except Exception as e:
            raise RuntimeError(f"Failed to detect board over WiFi: {e}") from e
    else:
        if port is None:
            port = find_port()
        try:
            uname_str = run(['exec', detect_code], port).strip()
        except Exception as e:
            raise RuntimeError(f"Failed to detect board over serial: {e}") from e

    # 检查是否包含 ESP32S3
    if 'ESP32S3' in uname_str:
        return (V3, ESP32S3)
    else:
        return (V2, ESP32)


# ── WiFi transport ────────────────────────────────────────────────────────────

def _wifi_cmd(host, cmd_byte, payload):
    """发送 WiFi 命令，返回响应 payload bytes"""
    import socket
    import struct

    s = socket.socket()
    s.settimeout(10)
    try:
        s.connect((host, 9595))
        # 发送请求 [1B cmd][4B len][payload]
        req = struct.pack('>BI', cmd_byte, len(payload)) + payload
        s.sendall(req)
        # 接收响应 [1B status][4B len][payload]，循环累积直到读满 5 字节
        hdr = b''
        while len(hdr) < 5:
            chunk = s.recv(5 - len(hdr))
            if not chunk:
                raise RuntimeError("Connection closed while reading response header")
            hdr += chunk

        status, length = struct.unpack('>BI', hdr)
        # 读取 payload，必须读满，否则视为协议错误
        data = b''
        while len(data) < length:
            chunk = s.recv(length - len(data))
            if not chunk:
                raise RuntimeError("Connection closed while reading response payload (expected %d, got %d)" % (length, len(data)))
            data += chunk
        if status != 0:
            raise RuntimeError(data.decode('utf-8'))
        return data
    finally:
        s.close()


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_run(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        if args.file:
            # WiFi 模式下 --file 应该先上传再执行，保持脚本语义
            import struct
            import tempfile
            import os

            # 上传文件到临时路径
            local_path = Path(args.file)
            remote_path = '/tmp_script.py'
            content = local_path.read_bytes()
            payload = struct.pack('>H', len(remote_path.encode('utf-8'))) + remote_path.encode('utf-8') + content
            _wifi_cmd(args.host, 0x02, payload)

            try:
                # 执行文件（设置 __file__ 和 __name__）
                code = f"__file__ = {remote_path!r}\nexec(open({remote_path!r}).read())"
                result = _wifi_cmd(args.host, 0x01, code.encode('utf-8'))

                if result and result != b'OK':
                    print(result.decode('utf-8'))
            finally:
                # 无论成功失败都清理临时文件
                try:
                    _wifi_cmd(args.host, 0x01, f"import os; os.remove('{remote_path}')".encode('utf-8'))
                except:
                    pass
        else:
            result = _wifi_cmd(args.host, 0x01, args.code.encode('utf-8'))
            if result and result != b'OK':
                print(result.decode('utf-8'))
    else:
        port = args.port or find_port()
        timeout = getattr(args, 'timeout', None)
        forward_stdin = getattr(args, 'stdin', False)
        if args.file:
            run(['run', args.file], port, capture=False,
                timeout=timeout, forward_stdin=forward_stdin)
        else:
            run(['exec', args.code], port, capture=False,
                timeout=timeout, forward_stdin=forward_stdin)


def _write_and_verify(port, local_path, remote_path, soft_reset=True, verify=True):
    """一次串口会话内完成上传与回读校验。

    分两次开串口会失败：mpremote 对设备加 flock 独占锁，同一进程持有会话时
    第二次打开必然拿不到锁。实测上传和校验必须在同一个 _transport 里。
    """
    data = Path(local_path).read_bytes()
    with _transport(port, soft_reset) as t:
        t.fs_writefile(remote_path, data)
        if verify:
            remote_size = t.fs_stat(remote_path).st_size
            if remote_size != len(data):
                raise RuntimeError(
                    "上传校验失败：%s 本地 %d 字节，板子上只有 %d 字节（缺 %d 字节）。"
                    "板子上的文件可能不完整，请重试；仍失败则检查串口线缆或降低波特率。"
                    % (remote_path, len(data), remote_size, len(data) - remote_size)
                )
    return len(data)


def cmd_put(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        import struct
        # 去掉 mpremote 风格的 : 前缀
        remote_path = args.remote.lstrip(':')
        path = remote_path.encode('utf-8')
        content = Path(args.local).read_bytes()
        payload = struct.pack('>H', len(path)) + path + content
        _wifi_cmd(args.host, 0x02, payload)
        if not getattr(args, 'no_verify', False):
            # 回读文件比对字节数，避免板端静默写残
            readback = _wifi_cmd(args.host, 0x03, path)
            if len(readback) != len(content):
                raise RuntimeError(
                    "上传校验失败：%s 本地 %d 字节，板子上只有 %d 字节（缺 %d 字节）。"
                    "请重试。"
                    % (remote_path, len(content), len(readback), len(content) - len(readback))
                )
        print(f"Uploaded {args.local} -> {remote_path} ({len(content)} bytes verified)")
    else:
        port = args.port or find_port()
        remote_path = args.remote.lstrip(':')
        verify = not getattr(args, 'no_verify', False)
        size = _write_and_verify(port, args.local, remote_path, verify=verify)
        if verify:
            print(f"Uploaded {args.local} -> {remote_path} ({size} bytes verified)")
        else:
            print(f"Uploaded {args.local} -> {remote_path} (unverified)")


def cmd_get(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        # 去掉 mpremote 风格的 : 前缀
        remote_path = args.remote.lstrip(':')
        path = remote_path.encode('utf-8')
        data = _wifi_cmd(args.host, 0x03, path)
        Path(args.local).write_bytes(data)
        print(f"Downloaded {remote_path} -> {args.local}")
    else:
        port = args.port or find_port()
        run(['cp', args.remote, args.local], port, capture=False)


def cmd_ls(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        path = (args.path or '/').encode('utf-8')
        result = _wifi_cmd(args.host, 0x04, path).decode('utf-8')
        print(result)
    else:
        port = args.port or find_port()
        path = args.path or '/'
        out = run(['exec', f'import os; [print(f) for f in os.listdir({path!r})]'], port)
        print(out, end='')


def cmd_flash(args):
    import esptool
    port = args.port or find_port()
    chip = args.chip or detect_board(port)[1]
    if not args.chip:
        print(f"Auto-detected chip: {chip}")

    esp = esptool.detect_chip(port, baud=460800)
    esp = esp.run_stub()
    esptool.write_flash(esp, [(0x0, args.firmware)], compress=True)
    esp.hard_reset()


def cmd_reset(args):
    """用 RTS 复位抢回被自启脚本独占的串口。

    自启脚本（boot.py/main.py 里的死循环）会抓住串口不放，Ctrl-C 和
    enter_raw_repl 都抢不回来。这里拉 EN 引脚物理复位芯片，趁启动窗口期
    拿回控制权。

    加 --grab 会在复位后立刻尝试进入 raw REPL 并保持住会话；不带 --grab
    则只复位就返回，串口随后会被自启脚本重新占回去。
    """
    import os
    import serial
    import time

    port = args.port or find_port()
    s = serial.Serial(port, 115200, timeout=0.1)
    try:
        if os.name == 'nt' and not args.soft:
            # Windows 上 USB 转串口桥接对 RTS 时序更敏感，用 esptool 的经典序列
            from esptool.reset import ClassicReset

            print(f"Hard resetting {port} via RTS pin...")
            ClassicReset(s)()
        else:
            # 简单的 RTS 拉低-释放：EN 拉低复位芯片，释放后芯片重启。
            # 实测这比 esptool 的 ClassicReset/UnixTightReset 都可靠——后者会
            # 多次切换控制线并 sleep，反而错过抢回串口的窗口。
            print(f"{'Soft' if args.soft else 'Hard'} resetting {port} via RTS pin...")
            s.dtr = False
            s.rts = True   # EN 拉低，芯片进入复位
            time.sleep(0.1)
            s.rts = False  # EN 释放，芯片重启
    except Exception as e:
        print(f"Warning: RTS reset failed ({e}); press the board's RST button instead.",
              file=sys.stderr)
    finally:
        s.close()

    if not getattr(args, 'grab', False):
        time.sleep(args.delay)
        print("Board reset; it is re-running boot.py. Give it a few seconds to boot.")
        return

    # 复位后必须马上开始抢：实测自启脚本约 0.9 秒后就开始刷提示符，
    # 中途等待太久窗口就过了。
    print("Reset done; grabbing the serial port back...", file=sys.stderr)
    try:
        with _transport(port, soft_reset=False, grab_attempts=args.attempts):
            print(f"Serial port recovered on {port}.", file=sys.stderr)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_screen(args):
    # 自动检测版本（如果未指定）
    version = args.version
    if not version and not (hasattr(args, 'transport') and args.transport == 'wifi'):
        port = args.port or find_port()
        _screen_auto_serial(port, args)
        return

    if not version:
        version, _ = detect_board(
            args.port,
            getattr(args, 'host', None),
            getattr(args, 'transport', 'serial')
        )
        print(f"Auto-detected: {version}")

    if hasattr(args, 'transport') and args.transport == 'wifi':
        version_byte = 0 if version == V2 else 1
        data = _wifi_cmd(args.host, 0x05, bytes([version_byte]))
        if version == V2:
            # v2: base64 解码 + ASCII art
            result = _screen_v2_ascii_from_b64(data)
        else:
            # v3: JSON pretty print
            result = json.dumps(json.loads(data.decode('utf-8')), indent=2, ensure_ascii=False)

        _write_screen_result(result, args)
    else:
        port = args.port or find_port()
        if version == V2:
            _screen_v2(port, args)
        else:
            _screen_v3(port, args)


def _screen_v2_ascii_from_b64(b64):
    raw = base64.b64decode(b64)
    rows = []
    for page in range(8):
        for bit in range(8):
            row = ''
            for col in range(128):
                byte = raw[page * 128 + col]
                row += '#' if (byte >> bit) & 1 else ' '
            rows.append(row)
    return '\n'.join(rows)


def _write_screen_result(result, args):
    if args.out:
        Path(args.out).write_text(result)
    else:
        print(result)


def _screen_auto_serial(port, args):
    code = (
        'import os, sys\n'
        'u=str(os.uname())\n'
        'if "ESP32S3" in u:\n'
        '    print("__HANDPY_VERSION__:v3")\n'
        '    import lv_displayer, lvgl as lv, json\n'
        '    def _get(o, names):\n'
        '        for n in names:\n'
        '            try: return getattr(o, n)()\n'
        '            except AttributeError: pass\n'
        '        return None\n'
        '    def _child_count(o):\n'
        '        for n in ("get_child_count", "get_child_cnt"):\n'
        '            try: return getattr(o, n)()\n'
        '            except AttributeError: pass\n'
        '        return 0\n'
        '    def _d(o):\n'
        '        if o is None: return {"type":"None"}\n'
        '        r={"type":str(type(o))}\n'
        '        for k, names in (("x",("get_x",)),("y",("get_y",)),("w",("get_width",)),("h",("get_height",))):\n'
        '            v=_get(o, names)\n'
        '            if v is not None: r[k]=v\n'
        '        try: r["text"]=o.get_text()\n'
        '        except: pass\n'
        '        ch=[]\n'
        '        for i in range(_child_count(o)):\n'
        '            try: ch.append(_d(o.get_child(i)))\n'
        '            except Exception as e: ch.append({"error":str(e)})\n'
        '        if ch: r["children"]=ch\n'
        '        return r\n'
        '    sys.stdout.write(json.dumps(_d(lv.screen_active())))\n'
        'else:\n'
        '    print("__HANDPY_VERSION__:v2")\n'
        '    import ubinascii\n'
        '    from mpython import oled\n'
        '    sys.stdout.write(ubinascii.b2a_base64(bytes(oled.buffer)).decode())\n'
    )
    out = run(['exec', code], port).strip()
    lines = out.splitlines()
    if not lines or not lines[0].startswith('__HANDPY_VERSION__:'):
        raise RuntimeError("Failed to parse screen response")
    version = lines[0].split(':', 1)[1]
    payload = '\n'.join(lines[1:]).strip()
    print(f"Auto-detected: {version}")
    if version == V2:
        result = _screen_v2_ascii_from_b64(payload)
    else:
        result = json.dumps(json.loads(payload), indent=2, ensure_ascii=False)
    _write_screen_result(result, args)


def _screen_v2(port, args):
    code = (
        'import sys, ubinascii\n'
        'from mpython import oled\n'
        'sys.stdout.write(ubinascii.b2a_base64(bytes(oled.buffer)).decode())\n'
    )
    b64 = run(['exec', code], port).strip()
    result = _screen_v2_ascii_from_b64(b64)
    _write_screen_result(result, args)


def _screen_v3(port, args):
    code = (
        'import lv_displayer, lvgl as lv, sys, json\n'
        'def _get(o, names):\n'
        '    for n in names:\n'
        '        try: return getattr(o, n)()\n'
        '        except AttributeError: pass\n'
        '    return None\n'
        'def _child_count(o):\n'
        '    for n in ("get_child_count", "get_child_cnt"):\n'
        '        try: return getattr(o, n)()\n'
        '        except AttributeError: pass\n'
        '    return 0\n'
        'def _d(o):\n'
        '    if o is None: return {"type":"None"}\n'
        '    r={"type":str(type(o))}\n'
        '    for k, names in (("x",("get_x",)),("y",("get_y",)),("w",("get_width",)),("h",("get_height",))):\n'
        '        v=_get(o, names)\n'
        '        if v is not None: r[k]=v\n'
        '    try: r["text"]=o.get_text()\n'
        '    except: pass\n'
        '    ch=[]\n'
        '    for i in range(_child_count(o)):\n'
        '        try: ch.append(_d(o.get_child(i)))\n'
        '        except Exception as e: ch.append({"error":str(e)})\n'
        '    if ch: r["children"]=ch\n'
        '    return r\n'
        'root=lv.screen_active()\n'
        'sys.stdout.write(json.dumps(_d(root)))\n'
    )
    out = run(['exec', code], port).strip()
    if args.out:
        Path(args.out).write_text(out)
    else:
        print(json.dumps(json.loads(out), indent=2, ensure_ascii=False))


def cmd_press(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        import struct
        type_byte = 0 if args.button else 1
        name = (args.button or args.touch).encode('utf-8')
        hold = args.hold or 100
        # 修复：字段顺序应为 [type][name_len][name][hold_ms]
        payload = struct.pack('>BB', type_byte, len(name)) + name + struct.pack('>H', hold)
        _wifi_cmd(args.host, 0x06, payload)
        print("Input simulated successfully")
    else:
        port = args.port or find_port()
        hold = args.hold or 100
        if args.button:
            _press_button(args.button, hold, port)
        elif args.touch:
            _press_touch(args.touch, hold, port)


def cmd_install(args):
    """部署 handpy_server 到板子"""
    port = args.port or find_port()

    # 1. 上传 handpy_server.py
    server_path = Path(__file__).parent / 'board' / 'handpy_server.py'
    if not server_path.exists():
        print(f"Error: {server_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Uploading handpy_server.py...")
    run(['resume', 'cp', str(server_path), ':handpy_server.py'], port, capture=False)

    # 2. 读取板子 boot.py
    print("Reading boot.py...")
    boot_content = _read_remote_text(port, 'boot.py', missing_ok=True)

    # 3. 检查是否已安装
    if '# HANDPY_SERVER_BEGIN' in boot_content:
        print("handpy_server already installed in boot.py")
        return

    # 4. 注入标记块
    injection = '\n# HANDPY_SERVER_BEGIN\nWIFI_CREDS = []\nimport handpy_server\n# HANDPY_SERVER_END\n'
    new_boot = boot_content + injection

    # 5. 写回 boot.py
    print("Updating boot.py...")
    _write_remote_text(port, 'boot.py', new_boot)

    print("Installation complete. Use 'wifi add' to configure WiFi credentials.")


def cmd_uninstall(args):
    """从板子移除 handpy_server"""
    import re
    port = args.port or find_port()

    # 1. 读取板子 boot.py
    print("Reading boot.py...")
    boot_content = _read_remote_text(port, 'boot.py')

    # 2. 删除标记块
    pattern = r'\n?# HANDPY_SERVER_BEGIN.*?# HANDPY_SERVER_END\n?'
    new_boot = re.sub(pattern, '', boot_content, flags=re.DOTALL)

    if new_boot == boot_content:
        print("handpy_server not found in boot.py")
    else:
        # 3. 写回 boot.py
        print("Updating boot.py...")
        _write_remote_text(port, 'boot.py', new_boot)

    # 4. 删除 handpy_server.py
    print("Removing handpy_server.py...")
    try:
        run(['resume', 'rm', ':handpy_server.py'], port, capture=False)
    except:
        print("Warning: Failed to remove handpy_server.py (may not exist)")

    print("Uninstallation complete.")


def cmd_wifi(args):
    """管理 WiFi 凭据"""
    import re
    import ast

    port = args.port or find_port()

    # 读取 boot.py
    boot_content = _read_remote_text(port, 'boot.py')

    # 提取 WIFI_CREDS
    match = re.search(r'# HANDPY_SERVER_BEGIN.*?WIFI_CREDS\s*=\s*(\[.*?\]).*?# HANDPY_SERVER_END',
                      boot_content, re.DOTALL)
    if not match:
        print("Error: handpy_server not installed. Run 'install' first.", file=sys.stderr)
        sys.exit(1)

    creds_str = match.group(1)
    try:
        creds = ast.literal_eval(creds_str)
    except:
        print("Error: Failed to parse WIFI_CREDS", file=sys.stderr)
        sys.exit(1)

    # 执行操作
    if args.action == 'add':
        new_cred = {'ssid': args.ssid, 'pwd': args.pwd}
        # 检查是否已存在
        if any(c['ssid'] == args.ssid for c in creds):
            print(f"Updating credentials for SSID: {args.ssid}")
            creds = [c if c['ssid'] != args.ssid else new_cred for c in creds]
        else:
            print(f"Adding credentials for SSID: {args.ssid}")
            creds.append(new_cred)
        _write_wifi_creds(boot_content, creds, port)

    elif args.action == 'list':
        if not creds:
            print("No WiFi credentials configured.")
        else:
            print("Configured WiFi credentials:")
            for i, c in enumerate(creds, 1):
                print(f"  {i}. SSID: {c['ssid']}")

    elif args.action == 'remove':
        original_len = len(creds)
        creds = [c for c in creds if c['ssid'] != args.ssid]
        if len(creds) == original_len:
            print(f"SSID not found: {args.ssid}")
        else:
            print(f"Removed credentials for SSID: {args.ssid}")
            _write_wifi_creds(boot_content, creds, port)


def _write_wifi_creds(boot_content, creds, port):
    """更新 boot.py 中的 WIFI_CREDS"""
    import re

    # 生成新的标记块
    creds_str = json.dumps(creds, ensure_ascii=False)
    new_block = f'# HANDPY_SERVER_BEGIN\nWIFI_CREDS = {creds_str}\nimport handpy_server\n# HANDPY_SERVER_END'

    # 替换标记块
    pattern = r'# HANDPY_SERVER_BEGIN.*?# HANDPY_SERVER_END'
    new_boot = re.sub(pattern, new_block, boot_content, flags=re.DOTALL)

    # 写回 boot.py
    _write_remote_text(port, 'boot.py', new_boot)
    print("boot.py updated successfully.")


def _read_remote_text(port, remote_path, missing_ok=False):
    path = remote_path.lstrip(':')
    try:
        with _transport(port, soft_reset=False) as t:
            return t.fs_readfile(path).decode('utf-8')
    except OSError as e:
        if missing_ok:
            return ''
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _write_remote_text(port, remote_path, content):
    path = remote_path.lstrip(':')
    try:
        with _transport(port, soft_reset=False) as t:
            t.fs_writefile(path, content.encode('utf-8'))
    except OSError as e:
        print(f"Error writing {path}: {e}", file=sys.stderr)
        sys.exit(1)


BUTTON_MAP = {'A': 'button_a', 'B': 'button_b'}
TOUCH_MAP = {
    'P': 'touchPad_P', 'Y': 'touchPad_Y', 'T': 'touchPad_T',
    'H': 'touchPad_H', 'O': 'touchPad_O', 'N': 'touchPad_N',
}


def _press_button(name, hold_ms, port):
    obj = BUTTON_MAP[name.upper()]
    code = (
        f'from mpython import {obj} as _b\n'
        f'from micropython import schedule\n'
        f'import time\n'
        f'class _FP:\n'
        f'    def value(self): return 0\n'
        f'    def irq(self,*a,**k): pass\n'
        f'_o=_b._Button__pin\n'
        f'_b._Button__pin=_FP()\n'
        f'_b._Button__was_pressed=True\n'
        f'_b._Button__pressed_count=min(_b._Button__pressed_count+1,100)\n'
        f'if _b.event_pressed: schedule(_b.event_pressed,_b._Button__pin)\n'
        f'time.sleep_ms({hold_ms})\n'
        f'_b._Button__pin=_o\n'
        f'if _b.event_released: schedule(_b.event_released,_o)\n'
    )
    run(['exec', code], port, capture=False)


def _press_touch(name, hold_ms, port):
    obj = TOUCH_MAP[name.upper()]
    code = (
        f'from mpython import {obj} as _t\n'
        f'import time\n'
        f'_t._Touch__value=1\n'
        f'_t._Touch__was_pressed=True\n'
        f'_t._Touch__pressed_count=min(_t._Touch__pressed_count+1,100)\n'
        f'if _t.event_pressed: _t.event_pressed(1)\n'
        f'time.sleep_ms({hold_ms})\n'
        f'_t._Touch__value=0\n'
        f'if _t.event_released: _t.event_released(0)\n'
    )
    run(['exec', code], port, capture=False)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description='HandPy board control tool')
    p.add_argument('--port', help='Serial port (auto-detect if omitted)')
    p.add_argument('--baud', type=int, default=115200)
    sub = p.add_subparsers(dest='cmd', required=True)

    serial_parent = argparse.ArgumentParser(add_help=False)
    serial_parent.add_argument('--port', default=argparse.SUPPRESS, help='Serial port (auto-detect if omitted)')
    serial_parent.add_argument('--baud', type=int, default=argparse.SUPPRESS)

    r = sub.add_parser('run', parents=[serial_parent], help='Run code on board')
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument('--code', help='Python code string')
    g.add_argument('--file', help='Local .py file to run')
    r.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    r.add_argument('--host', help='Board IP (wifi transport)')
    r.add_argument('--timeout', type=float, default=None,
                   help='Seconds of board silence before giving up (default: wait forever)')
    r.add_argument('--stdin', action='store_true',
                   help='Forward local stdin to the board, so input() works')
    r.set_defaults(func=cmd_run)

    pt = sub.add_parser('put', parents=[serial_parent], help='Upload file to board')
    pt.add_argument('local')
    pt.add_argument('remote')
    pt.add_argument('--no-verify', action='store_true',
                     help='Skip post-upload size verification')
    pt.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    pt.add_argument('--host', help='Board IP (wifi transport)')
    pt.set_defaults(func=cmd_put)

    gt = sub.add_parser('get', parents=[serial_parent], help='Download file from board')
    gt.add_argument('remote')
    gt.add_argument('local')
    gt.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    gt.add_argument('--host', help='Board IP (wifi transport)')
    gt.set_defaults(func=cmd_get)

    ls = sub.add_parser('ls', parents=[serial_parent], help='List files on board')
    ls.add_argument('--path', default='/')
    ls.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    ls.add_argument('--host', help='Board IP (wifi transport)')
    ls.set_defaults(func=cmd_ls)

    fl = sub.add_parser('flash', parents=[serial_parent], help='Flash firmware')
    fl.add_argument('--firmware', required=True)
    fl.add_argument('--chip', choices=['esp32', 'esp32s3'], help='Chip type (auto-detect if omitted)')
    fl.set_defaults(func=cmd_flash)

    rst = sub.add_parser('reset', parents=[serial_parent],
                         help='Reset the board (recovers a serial port held by a busy script)')
    rst.add_argument('--soft', action='store_true',
                     help='Use the lightweight RTS toggle instead of the full hard reset')
    rst.add_argument('--delay', type=float, default=2.0,
                     help='Seconds to wait after resetting (default: 2.0)')
    rst.add_argument('--grab', action='store_true',
                     help='Grab the serial port back right after resetting')
    rst.add_argument('--attempts', type=int, default=20,
                     help='How many times to retry grabbing the port (default: 20)')
    rst.set_defaults(func=cmd_reset)

    inst = sub.add_parser('install', parents=[serial_parent], help='Deploy handpy_server to board')
    inst.set_defaults(func=cmd_install)

    uninst = sub.add_parser('uninstall', parents=[serial_parent], help='Remove handpy_server from board')
    uninst.set_defaults(func=cmd_uninstall)

    wifi = sub.add_parser('wifi', parents=[serial_parent], help='Manage WiFi credentials')
    wifi_sub = wifi.add_subparsers(dest='action', required=True)

    wifi_add = wifi_sub.add_parser('add', parents=[serial_parent], help='Add WiFi credentials')
    wifi_add.add_argument('--ssid', required=True, help='WiFi SSID')
    wifi_add.add_argument('--pwd', required=True, help='WiFi password')

    wifi_list = wifi_sub.add_parser('list', parents=[serial_parent], help='List WiFi credentials')

    wifi_remove = wifi_sub.add_parser('remove', parents=[serial_parent], help='Remove WiFi credentials')
    wifi_remove.add_argument('--ssid', required=True, help='WiFi SSID')

    wifi.set_defaults(func=cmd_wifi)

    sc = sub.add_parser('screen', parents=[serial_parent], help='Read screen content')
    sc.add_argument('--version', choices=['v2', 'v3'], help='Board version (auto-detect if omitted)')
    sc.add_argument('--out', help='Output file (default: stdout)')
    sc.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    sc.add_argument('--host', help='Board IP (wifi transport)')
    sc.set_defaults(func=cmd_screen)

    pr = sub.add_parser('press', parents=[serial_parent], help='Simulate button/touch input')
    g2 = pr.add_mutually_exclusive_group(required=True)
    g2.add_argument('--button', choices=['A', 'B'])
    g2.add_argument('--touch', choices=['P', 'Y', 'T', 'H', 'O', 'N'])
    pr.add_argument('--hold', type=int, default=100, help='Hold duration ms')
    pr.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    pr.add_argument('--host', help='Board IP (wifi transport)')
    pr.set_defaults(func=cmd_press)

    return p


def main():
    try:
        parser = build_parser()
        args = parser.parse_args()
        if getattr(args, 'transport', None) == 'wifi' and not getattr(args, 'host', None):
            parser.error("--host is required when --transport wifi")
        args.func(args)
    except RuntimeError as e:
        # WiFi 命令错误（板端返回的错误信息）
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # 其他未预期的错误，显示简洁信息
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
