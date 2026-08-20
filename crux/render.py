"""Rendering, and the whole of the capability ladder.

Two ladders, detected independently because terminals mix and match:

* **Colour**: truecolour, 256, 16, none. `NO_COLOR` and a non-TTY force none.
* **Glyphs**: Nerd Font, Unicode box drawing, pure ASCII.

Inline markup rides the colour ladder. Content is authored with `backticks`
around anything you type, and `wrap_rich` turns those into styling; on a
terminal with no colour it leaves the marks alone instead, because there the
backticks are the only thing distinguishing a command from the prose around
it, and stripping them would delete the distinction rather than render it.

Screens never emit escape codes. They build `Text` out of styled spans and
semantic glyph names, and this module turns that into bytes at whatever rung
the terminal actually supports. That indirection is what lets `test.py` render
every screen at every rung and assert none of them loses a line or overflows,
which is the only way the ladder stays true once there are three tracks of
content pushing on it.

Nerd Font presence cannot be detected: no terminal reports its font. So the
default is Unicode, which is always safe, and Nerd glyphs are opt-in.


**Forked from hone (crux D4), deliberately, not shared.** Fixes here do not
flow back and are not expected to. Decision numbers below are crux's own;
where hone's plan is cited it is named as hone's.
"""

from __future__ import annotations

import os
import re
import sys
import textwrap
import unicodedata
from dataclasses import dataclass, field
from enum import IntEnum

from .theme import Color, Palette, get as get_palette

# --------------------------------------------------------------------------
# Capability levels
# --------------------------------------------------------------------------

class ColorLevel(IntEnum):
    NONE = 0
    C16 = 1
    C256 = 2
    TRUE = 3


class GlyphLevel(IntEnum):
    ASCII = 0
    UNICODE = 1
    NERD = 2


GLYPHS: dict[GlyphLevel, dict[str, str]] = {
    GlyphLevel.ASCII: {
        'tl': '+', 'tr': '+', 'bl': '+', 'br': '+', 'h': '-', 'v': '|',
        'htl': '+', 'htr': '+', 'hbl': '+', 'hbr': '+', 'hh': '=', 'hv': '|',
        'ltee': '+', 'rtee': '+', 'hltee': '+', 'hrtee': '+',
        'sel': '>', 'check': 'y', 'cross': 'x', 'dot_on': '*', 'dot_off': '.',
        'bar_on': '#', 'bar_off': '-', 'bullet': '.', 'arrow': '->',
        'up': '^', 'down': 'v', 'left': '<', 'right': '>',
        'enter': 'ret', 'ellipsis': '...',
        'note': '#', 'slot': '.',
    },
    GlyphLevel.UNICODE: {
        'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│',
        'htl': '┏', 'htr': '┓', 'hbl': '┗', 'hbr': '┛', 'hh': '━', 'hv': '┃',
        'ltee': '├', 'rtee': '┤', 'hltee': '┠', 'hrtee': '┨',
        'sel': '▸', 'check': '✓', 'cross': '✗', 'dot_on': '●', 'dot_off': '○',
        'bar_on': '█', 'bar_off': '░', 'bullet': '·', 'arrow': '→',
        'up': '↑', 'down': '↓', 'left': '←', 'right': '→',
        'enter': '⏎', 'ellipsis': '…',
        'note': '✎', 'slot': '·',
    },
}
# Nerd Font differs from Unicode only where a Nerd glyph is genuinely clearer.
GLYPHS[GlyphLevel.NERD] = dict(GLYPHS[GlyphLevel.UNICODE])


@dataclass(frozen=True, slots=True)
class Caps:
    color: ColorLevel
    glyphs: GlyphLevel
    palette: Palette
    cols: int = 80
    rows: int = 24

    def g(self, name: str) -> str:
        return GLYPHS[self.glyphs][name]


def detect_color(stream=None) -> ColorLevel:
    """Work out the colour rung from the environment.

    Order matters. `NO_COLOR` is honoured unconditionally because that is the
    point of the convention, and a non-TTY comes next so piping output never
    produces escape codes.
    """
    stream = stream or sys.stdout
    if os.environ.get('NO_COLOR') is not None:
        return ColorLevel.NONE
    try:
        if not stream.isatty():
            return ColorLevel.NONE
    except (AttributeError, ValueError):
        return ColorLevel.NONE

    term = os.environ.get('TERM', '')
    if term in ('dumb', ''):
        return ColorLevel.NONE
    if os.environ.get('COLORTERM', '').lower() in ('truecolor', '24bit'):
        return ColorLevel.TRUE
    if '256' in term:
        return ColorLevel.C256
    return ColorLevel.C16


def detect_glyphs() -> GlyphLevel:
    """Unicode when the encoding supports it, ASCII otherwise.

    Nerd Font is opt-in via `CRUX_NERD` because no terminal reports which
    font it is using, and guessing wrong fills the screen with tofu.
    """
    enc = (getattr(sys.stdout, 'encoding', None) or '').lower()
    if 'utf' not in enc:
        return GlyphLevel.ASCII
    if os.environ.get('CRUX_NERD'):
        return GlyphLevel.NERD
    return GlyphLevel.UNICODE


def detect_caps(theme: str | None = None, ascii_only: bool = False,
                cols: int = 80, rows: int = 24) -> Caps:
    color = detect_color()
    glyphs = GlyphLevel.ASCII if ascii_only else detect_glyphs()
    palette = get_palette(theme)
    # The ansi palette only has meaningful values at the sixteen-colour rung,
    # so asking for it caps the ladder there rather than inventing hex values.
    if palette.name == 'ansi' and color > ColorLevel.C16:
        color = ColorLevel.C16
    return Caps(color=color, glyphs=glyphs, palette=palette, cols=cols, rows=rows)


# --------------------------------------------------------------------------
# Styled text
# --------------------------------------------------------------------------

def char_width(ch: str) -> int:
    """Display width of one character.

    Zero-width combining marks and double-width CJK both exist in tool output
    the sift fixtures will carry, so width is measured rather than assumed to
    equal `len`.
    """
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1


def text_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def _sgr(caps: Caps, fg: Color | None, bg: Color | None, bold: bool) -> str:
    if caps.color == ColorLevel.NONE:
        return ''
    parts: list[str] = []
    if bold:
        parts.append('1')
    if fg is not None:
        if caps.color == ColorLevel.TRUE:
            r, g, b = fg.rgb
            parts.append(f'38;2;{r};{g};{b}')
        elif caps.color == ColorLevel.C256:
            parts.append(f'38;5;{fg.c256}')
        else:
            from .theme import ANSI16
            parts.append(str(ANSI16[fg.ansi]))
    if bg is not None:
        if caps.color == ColorLevel.TRUE:
            r, g, b = bg.rgb
            parts.append(f'48;2;{r};{g};{b}')
        elif caps.color == ColorLevel.C256:
            parts.append(f'48;5;{bg.c256}')
        else:
            from .theme import ANSI16
            parts.append(str(ANSI16[bg.ansi] + 10))
    return f'\x1b[{";".join(parts)}m' if parts else ''


@dataclass
class Span:
    text: str
    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False


@dataclass
class Text:
    """One display line, built from styled spans.

    Width is tracked over the plain text only, so a line's width is knowable
    without rendering it. That is what makes the overflow assertions in
    `test.py` meaningful at every rung of the ladder.
    """

    spans: list[Span] = field(default_factory=list)

    def add(self, text: str, fg: Color | None = None, bg: Color | None = None,
            bold: bool = False) -> Text:
        if text:
            self.spans.append(Span(text, fg, bg, bold))
        return self

    def width(self) -> int:
        return sum(text_width(s.text) for s in self.spans)

    def plain(self) -> str:
        return ''.join(s.text for s in self.spans)

    def pad_to(self, n: int, fg: Color | None = None, bg: Color | None = None) -> Text:
        gap = n - self.width()
        if gap > 0:
            self.add(' ' * gap, fg, bg)
        return self

    def truncate(self, n: int, ellipsis: str = '…') -> Text:
        """Clip to `n` columns, keeping styling. Never silently overflows."""
        if self.width() <= n:
            return self
        budget = max(0, n - text_width(ellipsis))
        out: list[Span] = []
        used = 0
        for s in self.spans:
            if used >= budget:
                break
            take = ''
            for ch in s.text:
                w = char_width(ch)
                if used + w > budget:
                    break
                take += ch
                used += w
            if take:
                out.append(Span(take, s.fg, s.bg, s.bold))
        out.append(Span(ellipsis, None, None, False))
        self.spans = out
        return self

    def render(self, caps: Caps) -> str:
        parts: list[str] = []
        for s in self.spans:
            code = _sgr(caps, s.fg, s.bg, s.bold)
            parts.append(f'{code}{s.text}\x1b[0m' if code else s.text)
        return ''.join(parts)


def wrap(s: str, width: int, indent: str = '') -> list[str]:
    """Wrap prose to `width`, preserving blank lines as paragraph breaks.

    `textwrap` collapses blank lines, which turns authored paragraphs into one
    wall of text, so paragraphs are split first and rejoined with the breaks
    intact.
    """
    out: list[str] = []
    for para in s.split('\n\n'):
        para = ' '.join(para.split())
        if not para:
            out.append('')
            continue
        out.extend(textwrap.wrap(para, max(8, width - len(indent)),
                                 initial_indent=indent,
                                 subsequent_indent=indent) or [''])
        out.append('')
    while out and out[-1] == '':
        out.pop()
    return out


# --------------------------------------------------------------------------
# Inline markup
# --------------------------------------------------------------------------

#: Content is authored with `backticks` around anything you type and `**bold**`
#: for the load-bearing sentence, because that is how technical prose is
#: written. Rendering the marks literally put 2367 stray backticks on screen
#: and made authored text look like unprocessed source, so they are parsed into
#: styling here instead.
CODE = 1
BOLD = 2

_MARKUP = re.compile(r'\*\*(.+?)\*\*|`([^`]+)`', re.DOTALL)


def parse_markup(s: str) -> list[tuple[str, int]]:
    """Explode a string into (character, style-mask) pairs.

    Per character rather than per span because wrapping happens afterwards and
    can cut a span anywhere. Bold is parsed first and its contents re-parsed,
    so ``**`-L` is local**`` comes out bold *and* code on the flag, which is
    exactly how it was written.
    """
    pairs: list[tuple[str, int]] = []
    pos = 0
    for m in _MARKUP.finditer(s):
        pairs += [(c, 0) for c in s[pos:m.start()]]
        if m.group(1) is not None:
            pairs += [(c, st | BOLD) for c, st in parse_markup(m.group(1))]
        else:
            pairs += [(c, CODE) for c in m.group(2)]
        pos = m.end()
    pairs += [(c, 0) for c in s[pos:]]
    return pairs


def strip_markup(s: str) -> str:
    """The text as it will be displayed, with the marks removed."""
    return ''.join(c for c, _ in parse_markup(s))


def _collapse(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Squeeze whitespace runs to one space, the way `wrap` does, in step."""
    out: list[tuple[str, int]] = []
    spaced = True
    for ch, st in pairs:
        if ch.isspace():
            if not spaced:
                out.append((' ', -1))      # style decided below
                spaced = True
        else:
            out.append((ch, st))
            spaced = False
    while out and out[-1][0] == ' ':
        out.pop()
    # A space inside one styled run joins it, so `ssh-keygen -t ed25519` is a
    # single span rather than five. Purely an output-size win: a space has no
    # ink, but every style change costs an escape sequence on every repaint.
    for i, (ch, st) in enumerate(out):
        if st != -1:
            continue
        prev = out[i - 1][1] if i else 0
        nxt = out[i + 1][1] if i + 1 < len(out) else 0
        out[i] = (ch, prev if prev == nxt else 0)
    return out


def wrap_rich(caps: Caps, s: str, width: int, indent: str, base: Color | None,
              code: Color | None = None) -> list[Text]:
    """`wrap`, but returning styled rows with inline markup applied.

    The line breaking is still `textwrap` over the display text, so wrapping
    is identical to what plain `wrap` would produce for the same visible
    characters. Styles are mapped back afterwards by locating each wrapped
    line in that text, which is exact: `textwrap` only ever slices.

    **A terminal with no colour keeps the marks.** Styling is the whole way a
    code span is distinguished once the backticks are gone, so stripping them
    on a monochrome terminal would delete the distinction rather than render
    it differently. That is the the capability ladder ladder applied to markup: the bottom rung
    is the marks themselves, which is exactly how the text was authored.
    """
    if caps.color == ColorLevel.NONE:
        return [Text().add(ln, base) if ln else Text()
                for ln in wrap(str(s), width, indent)]

    rows: list[Text] = []
    for para in str(s).split('\n\n'):
        pairs = _collapse(parse_markup(para))
        if not pairs:
            rows.append(Text())
            continue
        plain = ''.join(c for c, _ in pairs)
        styles = [st for _, st in pairs]
        lines = textwrap.wrap(plain, max(8, width - len(indent)),
                              initial_indent=indent,
                              subsequent_indent=indent) or ['']
        at = 0
        for ln in lines:
            body = ln[len(indent):] if ln.startswith(indent) else ln.lstrip()
            found = plain.find(body, at)
            if found < 0:                      # defensive: never lose a line
                rows.append(Text().add(ln, base))
                continue
            t = Text().add(indent)
            run = 0
            for i in range(1, len(body) + 1):
                if i < len(body) and styles[found + i] == styles[found + run]:
                    continue
                st = styles[found + run]
                t.add(body[run:i], code if (st & CODE) and code else base,
                      bold=bool(st & BOLD))
                run = i
            rows.append(t)
            at = found + len(body)
        rows.append(Text())
    while rows and not rows[-1].spans:
        rows.pop()
    return rows


def line(*args, **kwargs) -> Text:
    t = Text()
    if args or kwargs:
        t.add(*args, **kwargs)
    return t


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def box_top(caps: Caps, width: int, title: str = '', right: str = '',
            heavy: bool = False, color: Color | None = None) -> Text:
    """Top border, optionally with a left title and a right-aligned label."""
    p = caps.palette
    color = color or p.border
    tl = caps.g('htl' if heavy else 'tl')
    tr = caps.g('htr' if heavy else 'tr')
    h = caps.g('hh' if heavy else 'h')

    t = Text().add(tl, color)
    used = text_width(tl) + text_width(tr)
    if title:
        label = f'{h} {title} '
        t.add(h, color).add(f' {title} ', p.accent, bold=True)
        used += text_width(label)
    if right:
        rlabel = f' {right} '
        fill = max(0, width - used - text_width(rlabel) - 1)
        t.add(h * fill, color)
        t.add(rlabel, p.muted)
        t.add(h, color)
    else:
        t.add(h * max(0, width - used), color)
    t.add(tr, color)
    # A title plus right-label longer than the frame would otherwise push the
    # border past `width`. Rows clip themselves in box_row; the border must
    # hold the same line or the box tears open on exactly the screens whose
    # titles are long enough to matter.
    return t.truncate(width, caps.g('ellipsis'))


def box_bottom(caps: Caps, width: int, heavy: bool = False,
               color: Color | None = None) -> Text:
    p = caps.palette
    color = color or p.border
    bl = caps.g('hbl' if heavy else 'bl')
    br = caps.g('hbr' if heavy else 'br')
    h = caps.g('hh' if heavy else 'h')
    inner = max(0, width - text_width(bl) - text_width(br))
    return Text().add(bl + h * inner + br, color)


def box_sep(caps: Caps, width: int, heavy: bool = False,
            color: Color | None = None) -> Text:
    """Divider inside a box. Keeps the footer attached to the frame rather than
    floating below a closed border, which read as an unfinished box."""
    p = caps.palette
    color = color or p.border
    lt = caps.g('hltee' if heavy else 'ltee')
    rt = caps.g('hrtee' if heavy else 'rtee')
    h = caps.g('h')
    inner = max(0, width - text_width(lt) - text_width(rt))
    return Text().add(lt + h * inner + rt, color)


def box_row(caps: Caps, width: int, body: Text, heavy: bool = False,
            color: Color | None = None) -> Text:
    """Wrap one content line in vertical borders, padding or clipping to fit."""
    p = caps.palette
    color = color or p.border
    v = caps.g('hv' if heavy else 'v')
    inner = max(0, width - 2 * text_width(v))
    # Ellipsis comes from the glyph set: the default '…' is non-ASCII and would
    # leak at the ASCII rung the moment any line was long enough to clip.
    body.truncate(inner, caps.g('ellipsis')).pad_to(inner)
    t = Text().add(v, color)
    t.spans.extend(body.spans)
    t.add(v, color)
    return t


def bar(caps: Caps, pct: float, width: int = 10) -> Text:
    """Progress bar. Colour tracks how far along you are, not a fixed hue."""
    p = caps.palette
    pct = max(0.0, min(1.0, pct))
    filled = round(pct * width)
    colour = p.dim if pct == 0 else (p.ok if pct >= 0.999 else p.accent)
    return (Text()
            .add(caps.g('bar_on') * filled, colour)
            .add(caps.g('bar_off') * (width - filled), p.border))


def dots(caps: Caps, done: int, total: int, cap: int = 12) -> Text:
    """Progress dots, falling back to a count once there are too many.

    Thirty dots is not a glance-able progress indicator, it is noise. Past
    `cap` the same information reads better as a fraction.
    """
    p = caps.palette
    if total > cap:
        return (Text().add(f'{done}', p.accent, bold=True)
                      .add(f'/{total}', p.dim))
    return (Text()
            .add(caps.g('dot_on') * done, p.accent)
            .add(caps.g('dot_off') * max(0, total - done), p.border))


def footer(caps: Caps, hints: list[tuple[str, str]], width: int | None = None) -> Text:
    """The permanent key-hint footer. Every screen names its own way out.

    A screen with no hints is a bug, not a style choice, so this raises rather
    than rendering an empty bar. `test.py` asserts every screen produces one.
    """
    if not hints:
        raise ValueError('every screen must declare at least one key hint: every screen must declare at least one key hint')
    p = caps.palette
    t = Text()
    for i, (key, label) in enumerate(hints):
        if i:
            t.add('   ')
        t.add(key, p.accent, bold=True).add(' ' + label, p.muted)
    if width:
        t.truncate(width)
    return t


def render_lines(caps: Caps, lines: list[Text]) -> str:
    return '\n'.join(t.render(caps) for t in lines)
