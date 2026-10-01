"""Offline checks for handpy_tool: upload verification, streaming, error streams.

These stub out the serial transport so the logic can be exercised without a board.
"""
import io
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import handpy_tool  # noqa: E402


def make_args(**kw):
    base = dict(port='/dev/fake', transport='serial', host=None, no_verify=False,
                timeout=None, stdin=False, soft=False, delay=0.0)
    base.update(kw)
    return types.SimpleNamespace(**base)


class FakeStat:
    def __init__(self, size):
        self.st_size = size


class FakeTransport:
    """Stands in for SerialTransport; records what cmd_put would do."""

    instances = []

    def __init__(self, port, baudrate=115200, remote_size=None):
        self.port = port
        self.written = {}
        self.remote_size = remote_size
        self.executed = []
        FakeTransport.instances.append(self)

    def fs_writefile(self, dest, data):
        self.written[dest] = data

    def fs_stat(self, src):
        return FakeStat(self.remote_size if self.remote_size is not None
                        else len(self.written.get(src, b'')))

    def fs_readfile(self, src):
        return self.written.get(src, b'')

    def exec_raw_no_follow(self, command):
        self.executed.append(command)
        # reply to exec_raw_no_follow's prompt read
        self.serial.read(2)

    def enter_raw_repl(self, soft_reset=True, timeout_overall=10):
        self.entered = soft_reset

    def read_until(self, min_num_bytes, ending, **kw):
        return ending

    def follow(self, timeout=None, data_consumer=None):
        out, err = b"streamed output\n", b""
        if data_consumer:
            for i in range(len(out)):
                data_consumer(out[i:i + 1])
        return out, err

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    in_raw_repl = True

    def exit_raw_repl(self):
        pass

    def close(self):
        pass


def install_fake(monkey_remote_size=None):
    fake = FakeTransport('/dev/fake', remote_size=monkey_remote_size)
    fake.serial = types.SimpleNamespace(read=lambda n: b"OK", write=lambda b: None,
                                        inWaiting=lambda: 0)
    handpy_tool.SerialTransport = lambda port, baudrate=115200: fake
    return fake


class Capture(io.StringIO):
    """StringIO that advertises an encoding, like a real stdout."""

    encoding = 'utf-8'


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}{(' - ' + detail) if detail and not cond else ''}")
    return bool(cond)


results = []

# 1. put verifies size and succeeds when the board matches
local = Path('/home/frez79/HandPy-Skill/.claude/worktrees/fix-serial/_t.py')
local.write_bytes(b'print("hello")\n' * 40)
install_fake()
out = Capture()
so = sys.stdout
sys.stdout = out
try:
    handpy_tool.cmd_put(make_args(local=str(local), remote=':/t.py'))
finally:
    sys.stdout = so
results.append(check("put passes when sizes match", "verified" in out.getvalue(),
                     out.getvalue()))
local.unlink()

# 2. put must FAIL loudly when the board holds a truncated file
local = Path('/home/frez79/HandPy-Skill/.claude/worktrees/fix-serial/_t.py')
local.write_bytes(b'print("hello")\n' * 40)
expected = local.stat().st_size
install_fake(monkey_remote_size=expected - 700)  # simulate silent truncation
err = None
try:
    handpy_tool.cmd_put(make_args(local=str(local), remote=':/t.py'))
except RuntimeError as e:
    err = e
results.append(check("put raises on truncated upload", err is not None and "700" in str(err),
                     str(err)))
local.unlink()

# 3. --no-verify skips the check (escape hatch)
local = Path('/home/frez79/HandPy-Skill/.claude/worktrees/fix-serial/_t.py')
local.write_bytes(b'x' * 1000)
install_fake(monkey_remote_size=1)
out = Capture()
so = sys.stdout
sys.stdout = out
try:
    handpy_tool.cmd_put(make_args(local=str(local), remote=':/t.py', no_verify=True))
finally:
    sys.stdout = so
results.append(check("--no-verify skips verification", "unverified" in out.getvalue(),
                     out.getvalue()))
local.unlink()

# 4. streaming path streams instead of buffering until the end
fake = install_fake()
buf = Capture()
so = sys.stdout
sys.stdout = buf
try:
    handpy_tool.run_streaming(fake, "print('hi')", timeout=None)
finally:
    sys.stdout = so
results.append(check("run_streaming forwards output live", "streamed output" in buf.getvalue(),
                     buf.getvalue()))
results.append(check("run_streaming sent the code", len(fake.executed) == 1))

# 5. _exec_error_streams reads stdout+stderr on both mpremote layouts
from mpremote.transport import TransportExecError  # noqa: E402
so_stderr, err = handpy_tool._exec_error_streams(TransportExecError(1, "boom"))
results.append(check("error text lands on stderr", "boom" in err, err))
results.append(check("stdout bytes recovered", isinstance(so_stderr, bytes)))

class OldStyleErr(Exception):
    def __init__(self):
        super().__init__(b"partial out", "traceback here")

so2, err2 = handpy_tool._exec_error_streams(OldStyleErr())
results.append(check("legacy 2-tuple layout handled",
                     so2 == b"partial out" and err2 == "traceback here",
                     f"{so2!r} {err2!r}"))

print()
print(f"{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
