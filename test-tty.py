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
COLS, ROWS = 100, 40
SETTLE = 0.45

#: The app is launched with `--seed`, because a fixture built from the wall
#: clock puts the lead at a row this script cannot predict. Pinning it is what
#: makes "press Down N times" a legal instruction here.
SEED = 0
SCENARIO = 'sift-nmap-pinned'

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
                     [sys.executable, '-m', 'crux', '--no-alt-screen',
                      '--seed', str(SEED)])
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

    # Ask the content itself where the lead is at this seed, rather than
    # hardcoding a row that moves whenever a fixture gains a line.
    sys.path.insert(0, str(ROOT))
    from crux.loader import load
    sc = load().by_id(SCENARIO)
    lines = sc.body.build(SEED)
    lead_index = next(i for i, l in enumerate(lines) if l.kind == 'lead')

    d = Driver()
    try:
        home = d.send()
        ok('CRUX' in home, 'the picker renders its title')
        ok('sift' in home and 'salvage' in home and 'conduit' in home,
           'all three tracks are listed')
        ok('chain' in home, 'and the chain capstone')
        ok('scenario' in home,
           'the picker shows how much content each track has')
        ok('engine not built yet' not in home,
           'no track is still standing on a placeholder')
        ok('q quit' in home, 'the footer advertises a way out')

        track = d.send(b'\r')
        ok('graded' in track, 'the scenario list shows its tier')

        scan = d.send(b'\r')
        ok('nothing marked' in scan, 'the marking screen opens unmarked')
        ok('3000/tcp' in scan, 'the fixture is on screen')
        ok('spc mark' in scan and 'submit' in scan,
           'the marking screen advertises its own keys')
        ok(scan.count('ret ') <= 1,
           'the footer does not offer ret twice meaning two things')

        # Down to the lead, mark it. This is the assertion that pays for the
        # whole suite: it is the one `test.py` structurally cannot make.
        for _ in range(lead_index):
            d.send(b'\x1b[B')
        marked = d.send(b' ')
        ok('1 marked' in marked, 'space marks the line under the cursor')
        ok('3000/tcp' in marked, 'the marked line is still the lead')

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
        ok('attempted' in back, 'the attempt was recorded and shown')

        # salvage: the handover is the part no other suite can exercise. It
        # restores the terminal, runs a subprocess against a live loopback
        # target, and takes the terminal back.
        d.send(b'\x1b[B')
        salv = d.send(b'\r')
        ok('salvage' in salv, 'the salvage track opens')
        first = d.send(b'\r')
        ok('http://127.0.0.1:' in first, 'the screen names a loopback target')
        ok('e edit' in first and 'r run' in first,
           'the salvage screen advertises edit and run')
        ok('Read it before you run it' in first,
           'and says so before the first run')

        ran = d.send(b'r')
        ok('press Enter to return' in ran or 'Traceback' in ran
           or 'SyntaxError' in ran,
           'running hands the terminal over to a real subprocess')
        after = d.send(b'\r')
        ok('1 run' in after, 'the run was counted')
        ok('conditions met' in after or 'Closest attempt' in after,
           'and the screen reports how close it got')

        # conduit: the screen only. Building a network takes seconds and is
        # covered by test.py and validate.py; what this suite is for is that
        # the screen renders and offers its keys through a real terminal.
        # The picker keeps its cursor, and it is on salvage after the walk
        # above, so one Down reaches conduit rather than three.
        d.send(b'H')
        d.send(b'\x1b[B')
        cond = d.send(b'\r')
        ok('conduit' in cond, 'the conduit track opens')
        first = d.send(b'\r')
        ok('tunnel.sh' in first or 'cannot verify' in first,
           'the conduit screen names its script, or says it cannot verify')
        if 'cannot verify' not in first:
            ok('r build and run' in first, 'and offers to build the network')
            ok('key' in first, 'and tells you where the SSH key is')

        # chain: the capstone, driven from the picker into its first stage.
        d.send(b'H')
        # cursor is on conduit (row 3, index 2); one more Down reaches chain.
        d.send(b'\x1b[B')
        chain = d.send(b'\r')
        ok('chain' in chain or 'engagement' in chain.lower(),
           'the chain section opens')
        intro = d.send(b'\r')
        ok('Three stages' in intro or 'engagement' in intro.lower(),
           'the engagement brief shows')
        stage1 = d.send(b'\r')
        ok('Wexler' in stage1 or 'scan' in stage1.lower(),
           'and begin opens the first stage')
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
