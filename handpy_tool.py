#!/usr/bin/env python3
"""HandPy (mPython) board control tool."""

import argparse
import subprocess
import sys
import base64
import json
from pathlib import Path


# ── port detection ────────────────────────────────────────────────────────────

def find_port():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if any(x in (p.description or '') for x in ('CP210', 'CH340', 'FTDI', 'USB Serial')):
            return p.device
    if ports:
        return ports[0].device
    raise RuntimeError("No serial port found. Use --port to specify.")


# ── mpremote helpers ──────────────────────────────────────────────────────────

def mpremote_cmd(args, port):
    return ['mpremote', 'connect', port] + args


def run(args, port, capture=True):
    cmd = mpremote_cmd(args, port)
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            sys.exit(r.returncode)
        return r.stdout
    else:
        subprocess.run(cmd, check=True)


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
                code = f"exec(open('{remote_path}').read(), {{'__name__': '__main__', '__file__': '{remote_path}', '__builtins__': __builtins__}})"
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
        if args.file:
            run(['run', args.file], port, capture=False)
        else:
            run(['exec', args.code], port, capture=False)


def cmd_put(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        import struct
        # 去掉 mpremote 风格的 : 前缀
        remote_path = args.remote.lstrip(':')
        path = remote_path.encode('utf-8')
        content = Path(args.local).read_bytes()
        payload = struct.pack('>H', len(path)) + path + content
        _wifi_cmd(args.host, 0x02, payload)
        print(f"Uploaded {args.local} -> {remote_path}")
    else:
        port = args.port or find_port()
        run(['cp', args.local, args.remote], port, capture=False)


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
        out = run(['exec', f'import os; [print(f) for f in os.listdir("{path}")]'], port)
        print(out, end='')


def cmd_flash(args):
    chip = args.chip
    port = args.port or find_port()
    cmd = [
        'esptool.py', '--chip', chip, '--port', port,
        '--baud', '460800', 'write_flash', '-z', '0x0', args.firmware
    ]
    subprocess.run(cmd, check=True)


def cmd_screen(args):
    if hasattr(args, 'transport') and args.transport == 'wifi':
        version_byte = 0 if args.version == 'v2' else 1
        data = _wifi_cmd(args.host, 0x05, bytes([version_byte]))
        if args.version == 'v2':
            # v2: base64 解码 + ASCII art
            raw = base64.b64decode(data)
            rows = []
            for page in range(8):
                for bit in range(8):
                    row = ''
                    for col in range(128):
                        byte = raw[page * 128 + col]
                        row += '#' if (byte >> bit) & 1 else ' '
                    rows.append(row)
            result = '\n'.join(rows)
        else:
            # v3: JSON pretty print
            result = json.dumps(json.loads(data.decode('utf-8')), indent=2, ensure_ascii=False)

        if args.out:
            Path(args.out).write_text(result)
        else:
            print(result)
    else:
        port = args.port or find_port()
        if args.version == 'v2':
            _screen_v2(port, args)
        else:
            _screen_v3(port, args)


def _screen_v2(port, args):
    code = (
        'import sys, ubinascii\n'
        'from mpython import oled\n'
        'sys.stdout.write(ubinascii.b2a_base64(bytes(oled.buffer)).decode())\n'
    )
    b64 = run(['exec', code], port).strip()
    raw = base64.b64decode(b64)
    rows = []
    for page in range(8):
        for bit in range(8):
            row = ''
            for col in range(128):
                byte = raw[page * 128 + col]
                row += '#' if (byte >> bit) & 1 else ' '
            rows.append(row)
    result = '\n'.join(rows)
    if args.out:
        Path(args.out).write_text(result)
    else:
        print(result)


def _screen_v3(port, args):
    code = (
        'import lv_displayer, lvgl as lv, sys, json\n'
        'def _d(o):\n'
        '    r={"type":str(type(o)),"x":o.get_x(),"y":o.get_y(),"w":o.get_width(),"h":o.get_height()}\n'
        '    try: r["text"]=o.get_text()\n'
        '    except: pass\n'
        '    ch=[_d(o.get_child(i)) for i in range(o.get_child_cnt())]\n'
        '    if ch: r["children"]=ch\n'
        '    return r\n'
        'sys.stdout.write(json.dumps(_d(lv.screen_active())))\n'
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
    run(['cp', str(server_path), ':handpy_server.py'], port, capture=False)

    # 2. 读取板子 boot.py
    print("Reading boot.py...")
    boot_content = run(['cp', ':boot.py', '-'], port)

    # 3. 检查是否已安装
    if '# HANDPY_SERVER_BEGIN' in boot_content:
        print("handpy_server already installed in boot.py")
        return

    # 4. 注入标记块
    injection = '\n# HANDPY_SERVER_BEGIN\nWIFI_CREDS = []\nimport handpy_server\n# HANDPY_SERVER_END\n'
    new_boot = boot_content + injection

    # 5. 写回 boot.py
    print("Updating boot.py...")
    proc = subprocess.Popen(
        mpremote_cmd(['cp', '-', ':boot.py'], port),
        stdin=subprocess.PIPE,
        text=True
    )
    proc.communicate(new_boot)
    if proc.returncode != 0:
        print("Error: Failed to write boot.py", file=sys.stderr)
        sys.exit(1)

    print("Installation complete. Use 'wifi add' to configure WiFi credentials.")


def cmd_uninstall(args):
    """从板子移除 handpy_server"""
    import re
    port = args.port or find_port()

    # 1. 读取板子 boot.py
    print("Reading boot.py...")
    boot_content = run(['cp', ':boot.py', '-'], port)

    # 2. 删除标记块
    pattern = r'\n?# HANDPY_SERVER_BEGIN.*?# HANDPY_SERVER_END\n?'
    new_boot = re.sub(pattern, '', boot_content, flags=re.DOTALL)

    if new_boot == boot_content:
        print("handpy_server not found in boot.py")
    else:
        # 3. 写回 boot.py
        print("Updating boot.py...")
        proc = subprocess.Popen(
            mpremote_cmd(['cp', '-', ':boot.py'], port),
            stdin=subprocess.PIPE,
            text=True
        )
        proc.communicate(new_boot)
        if proc.returncode != 0:
            print("Error: Failed to write boot.py", file=sys.stderr)
            sys.exit(1)

    # 4. 删除 handpy_server.py
    print("Removing handpy_server.py...")
    try:
        run(['rm', ':handpy_server.py'], port, capture=False)
    except:
        print("Warning: Failed to remove handpy_server.py (may not exist)")

    print("Uninstallation complete.")


def cmd_wifi(args):
    """管理 WiFi 凭据"""
    import re
    import ast

    port = args.port or find_port()

    # 读取 boot.py
    boot_content = run(['cp', ':boot.py', '-'], port)

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
    proc = subprocess.Popen(
        mpremote_cmd(['cp', '-', ':boot.py'], port),
        stdin=subprocess.PIPE,
        text=True
    )
    proc.communicate(new_boot)
    if proc.returncode != 0:
        print("Error: Failed to write boot.py", file=sys.stderr)
        sys.exit(1)
    print("boot.py updated successfully.")


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

    r = sub.add_parser('run', help='Run code on board')
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument('--code', help='Python code string')
    g.add_argument('--file', help='Local .py file to run')
    r.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    r.add_argument('--host', help='Board IP (wifi transport)')
    r.set_defaults(func=cmd_run)

    pt = sub.add_parser('put', help='Upload file to board')
    pt.add_argument('local')
    pt.add_argument('remote')
    pt.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    pt.add_argument('--host', help='Board IP (wifi transport)')
    pt.set_defaults(func=cmd_put)

    gt = sub.add_parser('get', help='Download file from board')
    gt.add_argument('remote')
    gt.add_argument('local')
    gt.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    gt.add_argument('--host', help='Board IP (wifi transport)')
    gt.set_defaults(func=cmd_get)

    ls = sub.add_parser('ls', help='List files on board')
    ls.add_argument('--path', default='/')
    ls.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    ls.add_argument('--host', help='Board IP (wifi transport)')
    ls.set_defaults(func=cmd_ls)

    fl = sub.add_parser('flash', help='Flash firmware')
    fl.add_argument('--firmware', required=True)
    fl.add_argument('--chip', required=True, choices=['esp32', 'esp32s3'])
    fl.set_defaults(func=cmd_flash)

    inst = sub.add_parser('install', help='Deploy handpy_server to board')
    inst.set_defaults(func=cmd_install)

    uninst = sub.add_parser('uninstall', help='Remove handpy_server from board')
    uninst.set_defaults(func=cmd_uninstall)

    wifi = sub.add_parser('wifi', help='Manage WiFi credentials')
    wifi_sub = wifi.add_subparsers(dest='action', required=True)

    wifi_add = wifi_sub.add_parser('add', help='Add WiFi credentials')
    wifi_add.add_argument('--ssid', required=True, help='WiFi SSID')
    wifi_add.add_argument('--pwd', required=True, help='WiFi password')

    wifi_list = wifi_sub.add_parser('list', help='List WiFi credentials')

    wifi_remove = wifi_sub.add_parser('remove', help='Remove WiFi credentials')
    wifi_remove.add_argument('--ssid', required=True, help='WiFi SSID')

    wifi.set_defaults(func=cmd_wifi)

    sc = sub.add_parser('screen', help='Read screen content')
    sc.add_argument('--version', required=True, choices=['v2', 'v3'])
    sc.add_argument('--out', help='Output file (default: stdout)')
    sc.add_argument('--transport', choices=['serial', 'wifi'], default='serial')
    sc.add_argument('--host', help='Board IP (wifi transport)')
    sc.set_defaults(func=cmd_screen)

    pr = sub.add_parser('press', help='Simulate button/touch input')
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
        args = build_parser().parse_args()
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
