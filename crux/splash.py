"""The launch and exit sequences: a signal locking out of noise.

**Deliberately not hone's splash.** hone opens on one giant block wordmark that
dissolves in and out of random grit. crux opens on a **signal scope**: a
spectrum where a sharp peak climbs out of a noise floor and locks, which is the
app's own thesis made into its front door, because finding the one signal in a
screen of noise is exactly what `sift` trains and what the other two tracks pay
off. The wordmark is a compact letter-spaced label beneath the scope, not the
hero. Nothing here shares a silhouette with hone.

The engineering is still the careful kind an entrance needs: every write is
guarded so a splash can never be the thing that fails a launch, it degrades on
every rung (no TTY, a small window, `--no-splash`, or the ASCII rung all fall
back rather than print tofu), and a keypress skips it without skipping the app.
It holds for a key on the way in and names its own exit; the way out it just
plays, because leaving has already been decided.
"""

from __future__ import annotations

import math
import random

from .config import APP_TITLE, TAGLINE_PARTS
from .render import Caps, GlyphLevel, Text, render_lines, text_width

#: Scope geometry. The spectrum is HEIGHT bars tall; the frame adds a row above
#: and below. Interior width is chosen from the terminal, clamped to this band.
HEIGHT = 6
WIDTH_MIN = 26
WIDTH_MAX = 46

STEPS = 9
FRAME_SECONDS = 0.06
MIN_SECONDS = 0.45
HOLD_HINT = 'press any key'

OUT_STEPS = 8
OUT_FRAME_SECONDS = 0.06
OUT_HOLD_SECONDS = 0.6

HOLD_EMPTY_READS = 64

#: Never draw into a window the scope does not fit. The scope box, a gap, the
#: wordmark, the tagline, the note and the hint with a margin top and bottom.
MIN_COLS = WIDTH_MIN + 4
MIN_ROWS = HEIGHT + 8


def fits(caps: Caps) -> bool:
    return caps.cols >= MIN_COLS and caps.rows >= MIN_ROWS


def _width(caps: Caps) -> int:
    return max(WIDTH_MIN, min(WIDTH_MAX, caps.cols - 8))


def _bars(caps: Caps) -> str:
    """The fill glyph for the spectrum, top to bottom of a cell's worth."""
    return '#' if caps.glyphs == GlyphLevel.ASCII else '█'


def _heights(w: int, progress: float, rng) -> list[int]:
    """One integer 0..HEIGHT per column: a peak rising as the noise falls.

    At progress 0 it is all noise floor; at progress 1 the noise is gone and a
    clean symmetric spike stands at the centre. In between they cross, which is
    the signal emerging: the whole animation in one line of arithmetic.
    """
    centre = (w - 1) / 2
    sigma = max(1.4, w * 0.11)
    out = []
    for x in range(w):
        d = (x - centre) / sigma
        peak = math.exp(-0.5 * d * d) * progress
        noise = rng.random() * (1.0 - progress) * 0.5
        out.append(max(0, min(HEIGHT, round(max(peak, noise) * HEIGHT))))
    return out


def _scope(caps: Caps, progress: float, seed: int, status: str) -> list[Text]:
    """The framed spectrum: a titled box with the signal inside it."""
    p = caps.palette
    w = _width(caps)
    rng = random.Random(seed)
    heights = _heights(w, progress, rng)
    fill = _bars(caps)
    ascii_ = caps.glyphs == GlyphLevel.ASCII
    done = progress >= 0.999

    # Border and title glyphs degrade to ASCII.
    tl, tr, bl, br, h, v = (('+', '+', '+', '+', '-', '|') if ascii_
                            else ('╔', '╗', '╚', '╝', '═', '║'))
    bar_col = p.accent if done else (p.accent2 if progress > 0.45 else p.dim)
    frame_col = p.accent if done else p.border

    title = ' signal '
    top = Text().add(tl + h, frame_col).add(title, p.muted)
    top.add(h * max(0, w - text_width(title)), frame_col).add(h + tr, frame_col)

    rows = [top]
    for r in range(HEIGHT, 0, -1):
        body = ''.join(fill if hh >= r else ' ' for hh in heights)
        row = Text().add(v + ' ', frame_col).add(body, bar_col)
        row.add(' ' + v, frame_col)
        rows.append(row)

    label = f' {status} '
    bottom = Text().add(bl + h, frame_col)
    bottom.add(h * max(0, w - text_width(label)), frame_col)
    bottom.add(label, p.ok if done else p.dim).add(h + br, frame_col)
    rows.append(bottom)
    return rows


def _wordmark(caps: Caps, lit: bool) -> Text:
    """`C R U X`, letter-spaced. Small on purpose: the scope is the hero."""
    p = caps.palette
    gap = '   ' if caps.glyphs != GlyphLevel.ASCII else '  '
    return Text().add(gap.join(APP_TITLE), p.accent if lit else p.dim, bold=lit)


def _tagline(caps: Caps) -> str:
    return f' {caps.g("bullet")} '.join(TAGLINE_PARTS)


def _centre(s: str, cols: int) -> str:
    return s.center(cols).rstrip()


def _indent(pad: int, txt: Text) -> Text:
    """A copy of `txt` shifted right by `pad` columns."""
    out = Text().add(' ' * pad)
    out.spans.extend(txt.spans)
    return out


def _compose(caps: Caps, scope: list[Text], lit: bool, note: str,
             hold: bool) -> list[Text]:
    """Stack the scope, the wordmark, the tagline, the note and the hint,
    centred, with the vertical margin that keeps it settled on screen."""
    p = caps.palette
    w = _width(caps)
    show_note = bool(note) and lit and text_width(note) <= caps.cols - 2
    below = 4 + (2 if show_note else 0) + (2 if (hold and lit) else 0)
    top = max(1, (caps.rows - (HEIGHT + 2) - below) // 2)
    pad = max(0, (caps.cols - (w + 4)) // 2)

    rows: list[Text] = [Text() for _ in range(top)]
    for line in scope:
        rows.append(_indent(pad, line))
    rows.append(Text())
    word = _wordmark(caps, lit)
    rows.append(_indent(max(0, (caps.cols - word.width()) // 2), word))
    rows.append(Text().add(_centre(_tagline(caps), caps.cols), p.dim))
    if show_note:
        rows += [Text(), Text().add(_centre(note, caps.cols), p.accent2)]
    if hold and lit:
        rows += [Text(), Text().add(_centre(HOLD_HINT, caps.cols), p.muted)]
    return rows


def frame(caps: Caps, step: int, steps: int = STEPS, note: str = '',
          hold: bool = False) -> list[Text]:
    """One entrance frame: the peak part-way out of the noise."""
    progress = min(1.0, (step + 1) / steps)
    lit = progress >= 0.999
    status = 'locked' if lit else 'scanning'
    scope = _scope(caps, progress, seed=step * 7919, status=status)
    return _compose(caps, scope, lit, note, hold)


def out_frame(caps: Caps, step: int, steps: int = OUT_STEPS) -> list[Text]:
    """One exit frame: the peak collapsing back into noise."""
    span = max(1, steps - 1)
    progress = max(0.0, 1.0 - step / span)
    status = 'signal lost' if progress < 0.2 else 'releasing'
    scope = _scope(caps, progress, seed=104729 + step * 7919, status=status)
    return _compose(caps, scope, lit=False, note='', hold=False)


def farewell_frame(caps: Caps) -> list[Text]:
    """After the signal is gone: the wordmark and the tagline, held a beat."""
    p = caps.palette
    word = _wordmark(caps, lit=True)
    top = max(1, (caps.rows - 3) // 2)
    rows: list[Text] = [Text() for _ in range(top)]
    rows.append(_indent(max(0, (caps.cols - word.width()) // 2), word))
    rows += [Text(), Text().add(_centre(_tagline(caps), caps.cols), p.dim)]
    return rows


def scope_note(registry) -> str:
    """One line naming what loaded. Empty if it found nothing."""
    try:
        from .config import SECTIONS
        parts = [f'{len(registry.track(n).scenarios)} {n}'
                 for n in SECTIONS if registry.track(n).scenarios]
        return '   '.join(parts)
    except Exception:                                    # never break a launch
        return ''


# --------------------------------------------------------------------------
# Playback
# --------------------------------------------------------------------------

def _paint(tty, caps: Caps, rows: list[Text]) -> bool:
    try:
        tty.write('\x1b[2J\x1b[H'
                  + render_lines(caps, rows).replace('\n', '\r\n'))
        return True
    except Exception:
        return False


def play(tty, caps: Caps, note: str = '', hold: bool = True,
         clock=None) -> None:
    """Animate the entrance, then hold for a key. Never raises.

    A keypress during the animation ends it and counts as the key that
    releases the hold: someone skipping the entrance is not asking to press a
    second key. `hold=False` is the degraded floor for a caller with no
    keyboard.
    """
    import time
    clock = clock or time.monotonic
    if not fits(caps):
        return
    started = clock()
    skipped = drew = False
    for step in range(STEPS):
        drew = _paint(tty, caps, frame(caps, step)) or drew
        if not drew:
            break
        if not skipped:
            try:
                if tty.read_keys(timeout=FRAME_SECONDS):
                    skipped = True
            except Exception:
                time.sleep(FRAME_SECONDS)
    if not drew:
        return
    if not skipped and hold:
        if _paint(tty, caps, frame(caps, STEPS - 1, note=note, hold=True)):
            for _ in range(HOLD_EMPTY_READS):
                try:
                    if tty.read_keys(timeout=None):
                        break
                except Exception:
                    break
        return
    remaining = MIN_SECONDS - (clock() - started)
    if not skipped and remaining > 0:
        time.sleep(remaining)


def outro(tty, caps: Caps, hold: float = OUT_HOLD_SECONDS) -> None:
    """Play the exit. Never raises, never waits for a key."""
    import time
    if not fits(caps):
        return
    try:
        for step in range(OUT_STEPS):
            if not _paint(tty, caps, out_frame(caps, step)):
                return
            time.sleep(OUT_FRAME_SECONDS)
        if not _paint(tty, caps, farewell_frame(caps)):
            return
        if hold:
            time.sleep(hold)
        tty.write('\x1b[2J\x1b[H')
    except Exception:
        return
