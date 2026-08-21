"""The launch and exit sequences: CRUX scanning into a lock.

**Its own look, not hone's.** hone opens on a block wordmark that melts in and
out of random grit over the whole field at once. crux opens on a **scan-lock**:
a bright column sweeps left to right across a bold `CRUX`, and the letters snap
into focus behind the sweep while noise flickers ahead of it, until the whole
word locks. It is the app's signal-from-noise thesis turned into a directional
reveal, and it shares neither the font nor the mechanic with hone.

The engineering is the careful kind an entrance needs: every write is guarded
so a splash can never be the thing that fails a launch, it degrades on every
rung (no TTY, a small window, `--no-splash`, or the ASCII rung all fall back
rather than print tofu), and a keypress skips it without skipping the app. It
holds for a key on the way in and names its own exit; the way out it just
plays, because leaving has already been decided.
"""

from __future__ import annotations

import random

from .config import APP_TITLE, TAGLINE_PARTS
from .render import Caps, GlyphLevel, Text, render_lines, text_width

#: Bold, flat block CRUX (no drop shadow, so it does not read as hone). 54x7.
WORD_BOLD = [
    '    ████████  ██████████    ████    ████  ████    ████',
    '  ████        ████    ████  ████    ████  ████    ████',
    '  ████        ████    ████  ████    ████    ████████  ',
    '  ████        ██████████    ████    ████      ████    ',
    '  ████        ████  ████    ████    ████    ████████  ',
    '  ████        ████    ████  ████    ████  ████    ████',
    '    ████████  ████    ████    ████████    ████    ████',
]

#: A compact pure-ASCII CRUX for narrow windows and the ASCII glyph rung. 27x5.
WORD_ASCII = [
    ' ___ ___ _   _ _   _',
    '/ __| _ \\ | | |_| |_|',
    '| (_|   / |_| |>  <',
    ' \\___|_|_\\\\___//_/\\_\\',
    '',
]

#: What flickers ahead of the sweep, and what the letters lock out of.
NOISE_BLOCK = '░▒▓'
NOISE_ASCII = '.:+'

STEPS = 13
FRAME_SECONDS = 0.055
MIN_SECONDS = 0.45
HOLD_HINT = 'press any key to begin'

OUT_STEPS = 10
OUT_FRAME_SECONDS = 0.05
OUT_HOLD_SECONDS = 0.6

HOLD_EMPTY_READS = 64

MIN_COLS = 30
MIN_ROWS = 13


def fits(caps: Caps) -> bool:
    return caps.cols >= MIN_COLS and caps.rows >= MIN_ROWS


def _art(caps: Caps):
    """(rows, noise glyphs, scan glyph) for the widest wordmark that fits."""
    if caps.glyphs != GlyphLevel.ASCII and caps.cols >= len(WORD_BOLD[0]) + 4:
        return WORD_BOLD, NOISE_BLOCK, '█'
    return [r for r in WORD_ASCII], NOISE_ASCII, '|'


def _reveal(line: str, cut: int, edge: int, noise: str, scan: str,
            rng) -> list[tuple[str, int]]:
    """One art line as (char, role) pairs for a sweep at column `cut`.

    role 0 = revealed letter, 1 = the bright scan edge, 2 = noise ahead,
    -1 = plain space. The sweep is a two-column bright edge; behind it the real
    characters stand, ahead of it the field flickers with noise.
    """
    out: list[tuple[str, int]] = []
    for x, ch in enumerate(line):
        if x < edge:
            out.append((ch, -1 if ch == ' ' else 0))
        elif x <= cut:
            out.append((scan, 1))
        elif rng.random() < 0.14:
            out.append((noise[rng.randrange(len(noise))], 2))
        else:
            out.append((' ', -1))
    return out


def _wordmark(caps: Caps, progress: float, seed: int, locked: bool) -> list[Text]:
    p = caps.palette
    art, noise, scan = _art(caps)
    art = [r for r in art if r]                       # drop the ASCII pad line
    width = max(len(r) for r in art)
    rng = random.Random(seed)
    cut = int(progress * (width + 2))
    edge = max(0, cut - 1)

    rows: list[Text] = []
    for line in art:
        line = line.ljust(width)
        if locked:
            rows.append(Text().add(line, p.accent, bold=True))
            continue
        t = Text()
        run, run_role = '', None
        for ch, role in _reveal(line, cut, edge, noise, scan, rng):
            if role != run_role and run:
                t.add(run, {0: p.accent, 1: p.accent2, 2: p.dim}.get(run_role),
                      bold=(run_role in (0, 1)))
                run = ''
            run, run_role = run + ch, role
        if run:
            t.add(run, {0: p.accent, 1: p.accent2, 2: p.dim}.get(run_role),
                  bold=(run_role in (0, 1)))
        rows.append(t)
    return rows, width


def _tagline(caps: Caps) -> str:
    return f' {caps.g("bullet")} '.join(TAGLINE_PARTS)


def _centre(s: str, cols: int) -> str:
    return s.center(cols).rstrip()


def _indent(pad: int, txt: Text) -> Text:
    out = Text().add(' ' * pad)
    out.spans.extend(txt.spans)
    return out


def _compose(caps: Caps, word: list[Text], width: int, locked: bool,
             status: str, note: str, hold: bool) -> list[Text]:
    p = caps.palette
    ascii_ = caps.glyphs == GlyphLevel.ASCII
    show_note = bool(note) and locked and text_width(note) <= caps.cols - 2
    below = 4 + (2 if show_note else 0) + (2 if (hold and locked) else 0)
    top = max(1, (caps.rows - len(word) - below) // 2)
    pad = max(0, (caps.cols - width) // 2)

    rows: list[Text] = [Text() for _ in range(top)]
    for line in word:
        rows.append(_indent(pad, line))

    # A status readout under the wordmark: [ scanning ] / [ locked ].
    bar = '=' if ascii_ else '─'
    rule = Text().add(' ' * pad)
    rule.add(bar * max(0, width - text_width(status) - 4), p.border)
    rule.add(f' [ {status} ]', p.ok if locked else p.dim)
    rows.append(rule)

    rows.append(Text())
    rows.append(Text().add(_centre(_tagline(caps), caps.cols),
                           p.muted if locked else p.dim))
    if show_note:
        rows += [Text(), Text().add(_centre(note, caps.cols), p.accent2)]
    if hold and locked:
        rows += [Text(), Text().add(_centre(HOLD_HINT, caps.cols), p.accent,
                                    bold=True)]
    return rows


def frame(caps: Caps, step: int, steps: int = STEPS, note: str = '',
          hold: bool = False) -> list[Text]:
    """One entrance frame: the sweep part-way across the wordmark."""
    progress = min(1.0, (step + 1) / steps)
    locked = progress >= 0.999
    word, width = _wordmark(caps, progress, seed=step * 7919, locked=locked)
    status = 'locked' if locked else 'scanning'
    return _compose(caps, word, width, locked, status, note, hold)


def out_frame(caps: Caps, step: int, steps: int = OUT_STEPS) -> list[Text]:
    """One exit frame: the sweep retreating, the letters falling to noise."""
    span = max(1, steps - 1)
    progress = max(0.0, 1.0 - step / span)
    word, width = _wordmark(caps, progress, seed=104729 + step * 7919,
                            locked=False)
    status = 'signal lost' if progress < 0.2 else 'releasing'
    return _compose(caps, word, width, False, status, '', False)


def farewell_frame(caps: Caps) -> list[Text]:
    """After the sweep is gone: the locked wordmark and the tagline, a beat."""
    word, width = _wordmark(caps, 1.0, seed=0, locked=True)
    return _compose(caps, word, width, True, 'clear', '', False)


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
    """Animate the entrance, then hold for a key. Never raises."""
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
