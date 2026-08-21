"""The launch and exit sequences: the name resolving out of noise, and back.

**Forked from hone's splash (crux D4).** The mechanics are hone's and proven:
everything is guarded so an entrance can never be the thing that fails a
launch, everything degrades (no TTY, a small window, `--no-splash`, or the
ASCII rung all fall back rather than print tofu), and a keypress skips the
animation without skipping the work behind it.

**The metaphor is crux's own, and it is the app's whole thesis.** The letters
arrive as grit and resolve into `CRUX`, because finding the signal in the
noise is exactly what `sift` trains and what the other two tracks pay off. An
app whose entrance *is* the thing it teaches says more about itself than a
spinner ever could. The exit runs the same resolve backwards: the sharp name
comes apart into noise and goes dark, which is the right shape rather than a
second idea, and it costs almost nothing because it is the same `_resolve`
call with progress counting down.

**It waits for a key on the way in and never on the way out.** The held
entrance names its own exit (the screen contract), because a screen that sits
there without saying what a key does is indistinguishable from a hang, and this
one greets a first-time user. Quitting has already been decided, so the outro
just plays and leaves.
"""

from __future__ import annotations

import random
import time

from .config import APP_TITLE, TAGLINE_PARTS
from .render import Caps, GlyphLevel, Text, render_lines, text_width

#: ANSI Shadow, hand-assembled from the same glyph set hone's wordmark uses.
#: 36 columns wide, 6 tall.
BLOCK = [
    ' ██████╗ ██████╗  ██╗   ██╗ ██╗  ██╗',
    '██╔════╝ ██╔══██╗ ██║   ██║ ╚██╗██╔╝',
    '██║      ██████╔╝ ██║   ██║  ╚███╔╝ ',
    '██║      ██╔══██╗ ██║   ██║  ██╔██╗ ',
    '╚██████╗ ██║  ██║ ╚██████╔╝ ██╔╝ ██╗',
    ' ╚═════╝ ╚═╝  ╚═╝  ╚═════╝  ╚═╝  ╚═╝ ',
]

#: The pure-ASCII fallback for a terminal that cannot draw the blocks. A
#: screen of tofu is not an entrance, so the ASCII rung gets real letters.
PLAIN = [
    '  ____ ____  _   ___  __',
    ' / ___|  _ \\| | | \\ \\/ /',
    '| |   | |_) | | | |\\  / ',
    '| |___|  _ <| |_| |/  \\ ',
    ' \\____|_| \\_\\\\___//_/\\_\\',
]

#: The noise the letters resolve out of, sharpening as progress rises.
GRIT_BLOCK = '░▒▓█'
GRIT_PLAIN = '.:-='

STEPS = 7
FRAME_SECONDS = 0.07
MIN_SECONDS = 0.45

#: The held frame names its own exit (the screen contract).
HOLD_HINT = 'press any key'

#: The word for what is happening under the unresolved letters. It is also
#: what the animation is literally doing and what the whole app is for.
LOAD_WORD = 'resolving'

OUT_STEPS = 7
OUT_FRAME_SECONDS = 0.07
OUT_HOLD_SECONDS = 0.7
#: Under the wordmark as it comes apart: the reverse of the entrance.
OUT_WORD = 'dissolving'

#: A blocking read returning nothing is EOF or a dead stdin, not patience.
HOLD_EMPTY_READS = 64

#: Never draw into a window the block art does not fit. 38 is the art plus a
#: column either side; the rows cover the art, the rule, the tagline, the note
#: and the hint with a margin above and below.
MIN_COLS = 38
MIN_ROWS = 16


def art_for(caps: Caps) -> tuple[list[str], str]:
    if caps.glyphs == GlyphLevel.ASCII or caps.cols < len(BLOCK[0]) + 2:
        return PLAIN, GRIT_PLAIN
    return BLOCK, GRIT_BLOCK


def fits(caps: Caps) -> bool:
    return caps.cols >= MIN_COLS and caps.rows >= MIN_ROWS


def _resolve(line: str, progress: float, grit: str, rng) -> str:
    """One line of art, partially resolved.

    `progress` runs 0 to 1. A cell shows its real character once past a random
    threshold below `progress`; otherwise it is grit drawn from a band that
    itself sharpens as progress rises, so the noise is never static between
    frames.
    """
    if progress >= 1.0:
        return line
    out = []
    band = max(1, int(len(grit) * progress) + 1)
    for ch in line:
        if ch == ' ':
            out.append(' ')
        elif rng.random() < progress:
            out.append(ch)
        else:
            out.append(grit[rng.randrange(band)])
    return ''.join(out)


def _centre(s: str, cols: int) -> str:
    return s.center(cols).rstrip()


def frame(caps: Caps, step: int, steps: int = STEPS, seed: int | None = None,
          hold: bool = False, note: str = '') -> list[Text]:
    """One rendered frame of the entrance, as rows of styled text.

    `hold` adds the waiting-for-a-key line, and is only ever true on the
    resolved frame: an unresolved frame is still loading, and inviting a key
    there would be a lie about what it does. `note` is what the scope is, shown
    only once the letters have resolved.
    """
    p = caps.palette
    art, grit = art_for(caps)
    rng = random.Random(seed if seed is not None else step * 7919)
    progress = min(1.0, (step + 1) / steps)
    done = progress >= 1.0

    show_note = bool(note) and done and text_width(note) <= caps.cols - 2
    pad = max(0, (caps.cols - len(art[0])) // 2)
    below = 5 + (2 if show_note else 0)
    top = max(1, (caps.rows - len(art) - below) // 2)

    rows: list[Text] = [Text() for _ in range(top)]
    for ln in art:
        colour = p.accent if done else (
            p.accent2 if progress > 0.5 else p.border)
        rows.append(Text().add(' ' * pad + _resolve(ln, progress, grit, rng),
                               colour, bold=done))
    if done:
        rule = (caps.g('hh') if caps.glyphs != GlyphLevel.ASCII else '=') \
            * len(art[0])
        rows.append(Text().add(' ' * pad + rule, p.border))

    tag = f' {caps.g("bullet")} '.join(TAGLINE_PARTS)
    rows.append(Text())
    if done:
        rows.append(Text().add(_centre(tag, caps.cols), p.dim))
        if show_note:
            rows += [Text(), Text().add(_centre(note, caps.cols), p.accent2)]
        if hold:
            rows += [Text(), Text().add(_centre(HOLD_HINT, caps.cols), p.muted)]
    else:
        rows.append(Text().add(_centre(LOAD_WORD, caps.cols), p.dim))
    return rows


def out_frame(caps: Caps, step: int, steps: int = OUT_STEPS,
              seed: int | None = None) -> list[Text]:
    """One frame of the exit: the wordmark coming apart.

    Progress runs the other way from `frame`, so step 0 is still the sharp
    letters the entrance ended on and the last step is nearly all grit. The
    colour walks back down the ramp the entrance climbed, ending on the border
    colour, which on every palette is the closest visible thing to the
    background.
    """
    p = caps.palette
    art, grit = art_for(caps)
    rng = random.Random(seed if seed is not None else 104729 + step * 7919)
    span = max(1, steps - 1)
    progress = max(0.0, 1.0 - step / span)

    pad = max(0, (caps.cols - len(art[0])) // 2)
    top = max(1, (caps.rows - len(art) - 5) // 2)
    rows: list[Text] = [Text() for _ in range(top)]
    colour = (p.accent if progress > 0.66 else
              p.accent2 if progress > 0.33 else p.border)
    for ln in art:
        rows.append(Text().add(' ' * pad + _resolve(ln, progress, grit, rng),
                               colour))
    rule = (caps.g('hh') if caps.glyphs != GlyphLevel.ASCII else '=') \
        * len(art[0])
    rows.append(Text().add(' ' * pad + rule, p.border))
    rows += [Text(), Text().add(_centre(OUT_WORD, caps.cols), p.dim)]
    return rows


def farewell_frame(caps: Caps) -> list[Text]:
    """The last thing on screen after the letters have gone: the tagline alone.

    Held for a beat, because a dissolve that ends on an empty screen ends on
    nothing. The tagline is the one line worth carrying out of a session, and
    it is the three tracks read as the sentence they are.
    """
    p = caps.palette
    art, _ = art_for(caps)
    tag = f' {caps.g("bullet")} '.join(TAGLINE_PARTS)
    top = max(1, (caps.rows - 3) // 2)
    rows: list[Text] = [Text() for _ in range(top)]
    rows.append(Text().add(_centre(APP_TITLE, caps.cols), p.accent, bold=True))
    rows += [Text(), Text().add(_centre(tag, caps.cols), p.dim)]
    return rows


def scope_note(registry) -> str:
    """One line naming the scope of what loaded. Empty if it found nothing."""
    try:
        from .config import SECTIONS
        parts = []
        for name in SECTIONS:
            n = len(registry.track(name).scenarios)
            if n:
                parts.append(f'{n} {name}')
        return '  '.join(parts)
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
         clock=time.monotonic) -> None:
    """Animate the entrance, then hold for a key. Never raises.

    A keypress during the animation ends it early and counts as the key that
    releases the hold: someone who pressed a key to skip the entrance is asking
    to get on with it, not to press a second one. `hold=False` is the degraded
    floor for a caller that cannot present a keyboard.
    """
    if not fits(caps):
        return
    started = clock()
    skipped = False
    drew = False
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
    if skipped or not drew:
        if not drew:
            remaining = MIN_SECONDS - (clock() - started)
            if remaining > 0:
                time.sleep(remaining)
        return
    if not hold:
        remaining = MIN_SECONDS - (clock() - started)
        if remaining > 0:
            time.sleep(remaining)
        return
    if not _paint(tty, caps, frame(caps, STEPS - 1, hold=True, note=note)):
        return
    for _ in range(HOLD_EMPTY_READS):
        try:
            if tty.read_keys(timeout=None):
                break
        except Exception:
            break


def outro(tty, caps: Caps, hold: float = OUT_HOLD_SECONDS) -> None:
    """Play the exit. Never raises, never waits for a key.

    Quitting must not be the thing that fails, so every write is guarded and
    any trouble just ends the animation early: the caller has saved state and
    is on its way out regardless.
    """
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
