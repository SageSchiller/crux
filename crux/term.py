"""Terminal control: raw mode, alternate screen, and clean handover.

Everything here needs a real terminal, which is exactly why it is quarantined
in one module: `test.py` runs with no TTY, so nothing outside this
file may call `termios`. The decoding that turns bytes into keys lives in
`keys.py` and is pure, so it stays testable.

Three responsibilities:

* **Raw mode and the alternate screen**, restored on every exit path including
  exceptions, because a trainer that leaves your terminal wedged has failed at
  something more basic than teaching.
* **Kitty keyboard protocol negotiation** (unambiguous key decoding), detected by querying rather
  than by sniffing `$TERM`, which lies.
* **Suspend and resume** (the handover): give the terminal back exactly as we found it,
  run the real tool, take it back. This is what makes the contained experience
  work when the actual practice happens in real nvim.


**Forked from hone (crux D4), deliberately, not shared.** Fixes here do not
flow back and are not expected to. Decision numbers below are crux's own;
where hone's plan is cited it is named as hone's.
"""

from __future__ import annotations

import os
import select
import shutil
import signal
import sys
import termios
import tty
from contextlib import contextmanager

from . import keys as K
from .config import MIN_COLS, MIN_ROWS

# --------------------------------------------------------------------------
# Escape sequences
# --------------------------------------------------------------------------

ALT_SCREEN_ON = '\x1b[?1049h'
ALT_SCREEN_OFF = '\x1b[?1049l'
CURSOR_HIDE = '\x1b[?25l'
CURSOR_SHOW = '\x1b[?25h'
CLEAR = '\x1b[2J\x1b[H'

#: Push the disambiguate-escape-codes flag. This is the one that makes `C-i`
#: and `Tab` different events, which is the whole point of unambiguous key decoding.
KITTY_PUSH = '\x1b[>1u'
KITTY_POP = '\x1b[<u'
KITTY_QUERY = '\x1b[?u'
#: Primary device attributes. Every terminal answers it, which gives the Kitty
#: probe a reliable stopping point instead of a guessed timeout.
DA1_QUERY = '\x1b[c'


def is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def size() -> tuple[int, int]:
    """(cols, rows), clamped to the minimum the layout is authored against."""
    cols, rows = shutil.get_terminal_size(fallback=(MIN_COLS, MIN_ROWS))
    return max(cols, 20), max(rows, 6)


def too_small() -> bool:
    cols, rows = size()
    return cols < MIN_COLS or rows < MIN_ROWS


# --------------------------------------------------------------------------
# Kitty keyboard protocol
# --------------------------------------------------------------------------

def kitty_in_reply(buf: bytes) -> bool:
    """True if a Kitty keyboard-protocol reply appears in `buf`.

    A Kitty reply is `CSI ? <flags> u`; a DA1 reply is `CSI ? <params> c`. Both
    open the same way, so the final byte is what separates them. Pure, so
    `test.py` can exercise it without a terminal.

    At least one flag digit is required. A false positive here is the expensive
    direction: it would tell the student an ambiguous chord is expressible when
    their terminal cannot send it, which is the exact failure unambiguous key decoding exists to
    prevent. Malformed replies therefore read as unsupported.
    """
    for i in range(len(buf) - 1):
        if buf[i : i + 3] == b'\x1b[?':
            j = i + 3
            while j < len(buf) and buf[j : j + 1].isdigit():
                j += 1
            if j > i + 3 and buf[j : j + 1] == b'u':
                return True
    return False


def drain_input(timeout: float = 0.02) -> bytes:
    """Swallow anything still pending on stdin.

    Called after the capability probe: a terminal that answered DA1 slower than
    our timeout would otherwise have its reply decoded as user keystrokes, and
    the student would see phantom input at startup.
    """
    if not is_tty():
        return b''
    out = b''
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return out
        try:
            chunk = os.read(sys.stdin.fileno(), 1024)
        except OSError:
            return out
        if not chunk:
            return out
        out += chunk


def detect_kitty(timeout: float = 0.25) -> bool:
    """Ask the terminal whether it speaks the Kitty keyboard protocol.

    Sends the Kitty query followed by a primary-device-attributes query. Every
    terminal answers DA1, so the DA1 reply is the signal that the answer is
    complete: if a Kitty reply arrived before it, the protocol is supported. A
    terminal that ignores the Kitty query simply answers DA1 and we conclude
    'no' without waiting out a timeout.

    Must be called with the terminal already in raw mode.
    """
    if not is_tty():
        return False
    try:
        sys.stdout.write(KITTY_QUERY + DA1_QUERY)
        sys.stdout.flush()
    except OSError:
        return False

    buf = b''
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            break
        try:
            chunk = os.read(sys.stdin.fileno(), 1024)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        # DA1 replies as CSI ? ... c  (some terminals use CSI ... c).
        if b'c' in buf and b'\x1b[' in buf:
            break

    return kitty_in_reply(buf)


def kitty_supported() -> bool:
    """One-off Kitty probe for `--doctor`, outside any Terminal session.

    Enters raw mode just long enough to ask, restores unconditionally, and
    swallows any late reply so nothing leaks into the shell as phantom input.
    """
    if not is_tty():
        return False
    fd = sys.stdin.fileno()
    try:
        saved = termios.tcgetattr(fd)
    except termios.error:
        return False
    try:
        tty.setraw(fd)
        supported = detect_kitty()
        drain_input()
        return supported
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        except termios.error:
            pass


# --------------------------------------------------------------------------
# Terminal session
# --------------------------------------------------------------------------

class Terminal:
    """Owns the terminal for the lifetime of the app.

    Use as a context manager. Every exit path restores the terminal, including
    exceptions and signals, because the alternative is handing the user back a
    shell with no echo.
    """

    def __init__(self, use_alt_screen: bool = True) -> None:
        self.use_alt_screen = use_alt_screen
        self.kitty = False
        self._saved: list | None = None
        self._entered = False
        self._decoder = K.Decoder()
        self._prev_winch = None
        self.resized = False

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> Terminal:
        self._enter()
        return self

    def __exit__(self, *exc) -> None:
        self._exit()

    def _enter(self) -> None:
        if self._entered or not is_tty():
            self._entered = True
            return
        fd = sys.stdin.fileno()
        self._saved = termios.tcgetattr(fd)
        tty.setraw(fd)
        self.kitty = detect_kitty()
        drain_input()  # a late DA1 reply must not decode as phantom keystrokes
        self._decoder = K.Decoder(kitty=self.kitty)
        out = ''
        if self.use_alt_screen:
            out += ALT_SCREEN_ON
        out += CURSOR_HIDE + CLEAR
        if self.kitty:
            out += KITTY_PUSH
        self._write(out)
        self._prev_winch = signal.getsignal(signal.SIGWINCH)
        try:
            signal.signal(signal.SIGWINCH, self._on_winch)
        except ValueError:
            self._prev_winch = None  # not on the main thread; resize polls instead
        self._entered = True

    def _exit(self) -> None:
        if not self._entered:
            return
        self._entered = False
        if self._saved is None:
            return
        out = ''
        if self.kitty:
            out += KITTY_POP
        out += CURSOR_SHOW
        if self.use_alt_screen:
            out += ALT_SCREEN_OFF
        self._write(out)
        if self._prev_winch is not None:
            try:
                signal.signal(signal.SIGWINCH, self._prev_winch)
            except ValueError:
                pass
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved)
        except termios.error:
            pass
        self._saved = None

    def _on_winch(self, *_) -> None:
        self.resized = True

    # -- output ------------------------------------------------------------

    def _write(self, s: str) -> None:
        try:
            sys.stdout.write(s)
            sys.stdout.flush()
        except (OSError, ValueError):
            pass

    def write(self, s: str) -> None:
        self._write(s)

    def clear(self) -> None:
        self._write(CLEAR)

    # -- input -------------------------------------------------------------

    def read_keys(self, timeout: float | None = None) -> list[K.Key]:
        """Block until at least one key is available, or `timeout` elapses.

        The flush-on-timeout is what resolves a lone `Esc`: it is held back in
        case it begins a longer sequence, and released once nothing follows.
        """
        if not is_tty():
            return []
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return self._decoder.flush()
        try:
            data = os.read(sys.stdin.fileno(), 1024)
        except OSError:
            return []
        if not data:
            return []
        out = self._decoder.feed(data)
        if out:
            return out
        # Held an incomplete sequence. Give the rest a brief moment to arrive,
        # then force a decision rather than blocking on a key that never comes.
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            try:
                out = self._decoder.feed(os.read(sys.stdin.fileno(), 1024))
            except OSError:
                out = []
        return out or self._decoder.flush()

    # -- handover (the handover) ----------------------------------------------------

    @contextmanager
    def suspended(self):
        """Give the terminal back, run something real, take it back.

        This is the handover. The student does the work in the actual tool and the
        trainer picks up where it left off, which is the same handover pattern
        `git` uses for `$EDITOR` and therefore already familiar.
        """
        was_entered = self._entered
        if was_entered:
            self._exit()
        try:
            yield
        finally:
            if was_entered:
                self._enter()


@contextmanager
def managed(use_alt_screen: bool = True):
    """Convenience wrapper so callers never hand-roll the try/finally."""
    t = Terminal(use_alt_screen=use_alt_screen)
    try:
        t._enter()
        yield t
    finally:
        t._exit()
