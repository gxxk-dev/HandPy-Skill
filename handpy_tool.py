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


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_run(args):
    port = args.port or find_port()
    if args.file:
        run(['run', args.file], port, capture=False)
    else:
        run(['exec', args.code], port, capture=False)


def cmd_put(args):
    port = args.port or find_port()
    run(['cp', args.local, args.remote], port, capture=False)


def cmd_get(args):
    port = args.port or find_port()
    run(['cp', args.remote, args.local], port, capture=False)


def cmd_ls(args):
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
        'import lvgl as lv, sys, json\n'
        'def _d(o):\n'
        '    r={"type":str(type(o)),"x":o.get_x(),"y":o.get_y(),"w":o.get_width(),"h":o.get_height()}\n'
        '    try: r["text"]=o.get_text()\n'
        '    except: pass\n'
        '    ch=[_d(o.get_child(i)) for i in range(o.get_child_cnt())]\n'
        '    if ch: r["children"]=ch\n'
        '    return r\n'
        'sys.stdout.write(json.dumps(_d(lv.scr_act())))\n'
    )
    out = run(['exec', code], port).strip()
    if args.out:
        Path(args.out).write_text(out)
    else:
        print(json.dumps(json.loads(out), indent=2, ensure_ascii=False))


def cmd_press(args):
    port = args.port or find_port()
    hold = args.hold or 100
    if args.button:
        _press_button(args.button, hold, port)
    elif args.touch:
        _press_touch(args.touch, hold, port)


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
    r.set_defaults(func=cmd_run)

    pt = sub.add_parser('put', help='Upload file to board')
    pt.add_argument('local')
    pt.add_argument('remote')
    pt.set_defaults(func=cmd_put)

    gt = sub.add_parser('get', help='Download file from board')
    gt.add_argument('remote')
    gt.add_argument('local')
    gt.set_defaults(func=cmd_get)

    ls = sub.add_parser('ls', help='List files on board')
    ls.add_argument('--path', default='/')
    ls.set_defaults(func=cmd_ls)

    fl = sub.add_parser('flash', help='Flash firmware')
    fl.add_argument('--firmware', required=True)
    fl.add_argument('--chip', required=True, choices=['esp32', 'esp32s3'])
    fl.set_defaults(func=cmd_flash)

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
    pr.set_defaults(func=cmd_press)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
