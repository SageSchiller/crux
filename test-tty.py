#!/usr/bin/env python3
"""The third suite: drives the real app in a real pty.

`test.py` covers the pure layers and drives the screen stack directly. It
cannot see anything that goes wrong between a terminal's bytes and a `Key`,
because it builds its input with `keys.parse`, which is asking the notation
whether it agrees with itself.

That gap was not hypothetical. For the whole of Phase 0 the space bar did
nothing on the marking screen: the decoder produced `Key(' ')` and every screen
compared against `parse('SPC')`. Twelve thousand green checks did not touch it.
This suite found it on the first run, which is the argument for its existence.

**Not authoritative, and allowed to skip.** It needs a pty and a working
`python3 -m crux`; where it cannot run it says so and exits 0 rather than
failing a build for an absence. `test.py` remains the suite that must be green.
"""

from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import struct
import sys
import tempfile
import termios
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLS, ROWS = 90, 30
SETTLE = 0.45

CHECKS = 0
FAILURES: list[str] = []

_SGR = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')


def ok(cond: bool, what: str) -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(what)


def strip(s: str) -> str:
    return _SGR.sub('', s)


class Driver:
    """A crux process on the other end of a pty."""

    def __init__(self) -> None:
        self.home = tempfile.mkdtemp(prefix='crux-tty-')
        self.pid, self.fd = pty.fork()
        if self.pid == 0:                                  # child
            os.environ['TERM'] = 'xterm-256color'
            os.environ['COLORTERM'] = 'truecolor'
            os.environ['XDG_DATA_HOME'] = self.home
            os.chdir(str(ROOT))
            os.execv(sys.executable,
                     [sys.executable, '-m', 'crux', '--no-alt-screen'])
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                    struct.pack('HHHH', ROWS, COLS, 0, 0))

    def send(self, data: bytes = b'') -> str:
        """Send keys, wait for the repaint, return the last full frame."""
        if data:
            os.write(self.fd, data)
        time.sleep(SETTLE)
        chunk = b''
        while select.select([self.fd], [], [], 0.15)[0]:
            try:
                d = os.read(self.fd, 65536)
            except OSError:
                break
            if not d:
                break
            chunk += d
        # The app repaints on a timeout, so a read holds several identical
        # frames. The last one after a clear is the current screen.
        frames = chunk.decode('utf-8', 'replace').split('\x1b[2J\x1b[H')
        return strip(frames[-1] if frames else '')

    def close(self) -> int:
        try:
            os.write(self.fd, b'q')
            time.sleep(0.3)
        except OSError:
            pass
        try:
            os.close(self.fd)
        except OSError:
            pass
        _, status = os.waitpid(self.pid, 0)
        return os.waitstatus_to_exitcode(status) if hasattr(
            os, 'waitstatus_to_exitcode') else status


def main() -> int:
    if not hasattr(os, 'openpty'):
        print('skipped: no pty on this platform')
        return 0

    d = Driver()
    try:
        home = d.send()
        ok('CRUX' in home, 'the picker renders its title')
        ok('sift' in home and 'salvage' in home and 'conduit' in home,
           'all three tracks are listed')
        ok('engine not built yet' in home,
           'unbuilt tracks say so on the picker')
        ok('q quit' in home, 'the footer advertises a way out')

        track = d.send(b'\r')
        ok('graded' in track, 'the scenario list shows its tier')

        scan = d.send(b'\r')
        ok('nothing marked' in scan, 'the marking screen opens unmarked')
        ok('3000/tcp' in scan, 'the fixture is on screen')
        ok('spc mark' in scan and 'ret submit' in scan,
           'the marking screen advertises its own keys')

        # Down to the lead, mark it. This is the assertion that pays for the
        # whole suite: it is the one `test.py` structurally cannot make.
        for _ in range(8):
            d.send(b'\x1b[B')
        marked = d.send(b' ')
        ok('1 marked' in marked, 'space marks the line under the cursor')
        ok('[' in marked, 'the mark renders in the checkbox')

        unmarked = d.send(b' ')
        ok('nothing marked' in unmarked, 'space toggles back off')
        d.send(b' ')

        act = d.send(b'\r')
        ok('and now what' in act, 'submitting reaches the act beat')
        ok('You marked 1 line' in act, 'the act beat counts the marks')

        result = d.send(b'\r')
        ok('found 1 of 1' in result, 'the correct mark is scored as found')
        ok('chased nothing' in result, 'nothing was chased')
        ok('clean pass' in result, 'a perfect run reports a clean pass')
        ok('Waypoint node' in result, 'the result links back to Waypoint')

        back = d.send(b'H')
        ok('CRUX' in back, 'H returns to the picker from three deep')
        ok('1/1 attempted' in back, 'the attempt was recorded and shown')
    finally:
        code = d.close()

    ok(code == 0, f'the app exits cleanly on q (got {code})')

    if FAILURES:
        for f in FAILURES:
            print(f'  FAIL  {f}')
        print(f'{len(FAILURES)} failure(s) in {CHECKS} checks')
        return 1
    print(f'green: {CHECKS} checks against a real pty')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
