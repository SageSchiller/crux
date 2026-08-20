"""Palettes and the colour half of the capability ladder.

Every colour carries all three rungs at once: a truecolour hex, a 256-colour
index derived from it, and a named ANSI-16 fallback. Rendering picks the rung
the terminal actually supports rather than assuming the best case.

The default palette is lifted from the author's own `doom-cyberpunk-neon`
theme, which already carries per-rung values because Doom themes are authored
that way. That is why crux looks like part of this machine rather than a
visitor: same colours as ghostty, tmux, fish, Doom, and neovim.


**Forked from hone (crux D4), deliberately, not shared.** Fixes here do not
flow back and are not expected to. Decision numbers below are crux's own;
where hone's plan is cited it is named as hone's.
"""

from __future__ import annotations

from dataclasses import dataclass

ANSI16 = {
    'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
    'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
    'brightblack': 90, 'brightred': 91, 'brightgreen': 92, 'brightyellow': 93,
    'brightblue': 94, 'brightmagenta': 95, 'brightcyan': 96, 'brightwhite': 97,
}


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _to_256(h: str) -> int:
    """Nearest xterm-256 index for a hex colour.

    The 256 palette is 16 fixed colours, a 6x6x6 RGB cube at 16-231, and 24
    greys at 232-255. Compare the best cube match against the best grey match
    and take whichever is closer, which matters for this palette because its
    backgrounds are near-grey blues that the cube renders badly.
    """
    r, g, b = _hex_rgb(h)
    levels = (0, 95, 135, 175, 215, 255)

    def nearest(v: int) -> int:
        return min(range(6), key=lambda i: abs(levels[i] - v))

    ri, gi, bi = nearest(r), nearest(g), nearest(b)
    cube = 16 + 36 * ri + 6 * gi + bi
    cube_err = ((levels[ri] - r) ** 2 + (levels[gi] - g) ** 2 + (levels[bi] - b) ** 2)

    grey_v = round((r + g + b) / 3)
    gi2 = min(23, max(0, round((grey_v - 8) / 10)))
    grey_level = 8 + 10 * gi2
    grey_err = ((grey_level - r) ** 2 + (grey_level - g) ** 2 + (grey_level - b) ** 2)

    return cube if cube_err <= grey_err else 232 + gi2


@dataclass(frozen=True, slots=True)
class Color:
    """One colour at all three rungs of the ladder."""

    hex: str
    ansi: str  # ANSI16 name used when only sixteen colours are available

    @property
    def rgb(self) -> tuple[int, int, int]:
        return _hex_rgb(self.hex)

    @property
    def c256(self) -> int:
        return _to_256(self.hex)


@dataclass(frozen=True, slots=True)
class Palette:
    """Semantic roles, never raw colours at the call site.

    Screens ask for `accent` or `err`, never for cyan or red, so a new palette
    is a drop-in and `--theme ansi` can map every role onto the terminal's own
    sixteen colours without touching a single screen.
    """

    name: str
    bg: Color
    panel: Color
    border: Color
    dim: Color
    muted: Color
    fg: Color
    accent: Color
    accent2: Color
    ok: Color
    warn: Color
    err: Color
    info: Color
    sel_bg: Color
    sel_fg: Color


#: The author's own palette. Values taken from
#: ~/.config/doom/themes/doom-cyberpunk-neon-theme.el, which supplies its own
#: 16-colour fallbacks; those are reused verbatim rather than guessed.
CYBERPUNK_NEON = Palette(
    name='cyberpunk-neon',
    bg=Color('#070b16', 'black'),
    panel=Color('#131a2b', 'brightblack'),
    border=Color('#24345c', 'brightblack'),
    dim=Color('#5a6b94', 'brightblack'),
    muted=Color('#7d8cb0', 'brightblack'),
    fg=Color('#dce7ff', 'white'),
    accent=Color('#00f0ff', 'brightcyan'),
    accent2=Color('#ff5fd7', 'brightmagenta'),
    ok=Color('#72f1b8', 'green'),
    warn=Color('#ffd479', 'yellow'),
    err=Color('#ff5f8f', 'red'),
    info=Color('#6cb6ff', 'brightblue'),
    sel_bg=Color('#24345c', 'blue'),
    sel_fg=Color('#dce7ff', 'brightwhite'),
)

#: Shipped for everyone who is not the author, per the capability ladder. Deliberately duller:
#: it has to sit on top of whatever background the stranger's terminal uses,
#: so it leans on contrast rather than on saturation.
NEUTRAL = Palette(
    name='neutral',
    bg=Color('#101014', 'black'),
    panel=Color('#1c1c22', 'brightblack'),
    border=Color('#3a3a45', 'brightblack'),
    dim=Color('#6a6a78', 'brightblack'),
    muted=Color('#9a9aa8', 'white'),
    fg=Color('#e6e6ec', 'brightwhite'),
    accent=Color('#5fd7d7', 'cyan'),
    accent2=Color('#d78fd7', 'magenta'),
    ok=Color('#87d787', 'green'),
    warn=Color('#d7c07f', 'yellow'),
    err=Color('#d78787', 'red'),
    info=Color('#87afd7', 'blue'),
    sel_bg=Color('#3a3a45', 'blue'),
    sel_fg=Color('#ffffff', 'brightwhite'),
)

#: `--theme ansi`: inherit whatever the user already likes. Hex values are
#: placeholders that are never consulted, because this palette is only ever
#: rendered at the sixteen-colour rung.
ANSI = Palette(
    name='ansi',
    bg=Color('#000000', 'black'),
    panel=Color('#000000', 'black'),
    border=Color('#808080', 'brightblack'),
    dim=Color('#808080', 'brightblack'),
    muted=Color('#c0c0c0', 'white'),
    fg=Color('#ffffff', 'brightwhite'),
    accent=Color('#00ffff', 'brightcyan'),
    accent2=Color('#ff00ff', 'brightmagenta'),
    ok=Color('#00ff00', 'green'),
    warn=Color('#ffff00', 'yellow'),
    err=Color('#ff0000', 'red'),
    info=Color('#0000ff', 'brightblue'),
    sel_bg=Color('#0000ff', 'blue'),
    sel_fg=Color('#ffffff', 'brightwhite'),
)

PALETTES = {p.name: p for p in (CYBERPUNK_NEON, NEUTRAL, ANSI)}
DEFAULT = CYBERPUNK_NEON


def get(name: str | None) -> Palette:
    """Look up a palette by name, falling back to the default."""
    if not name:
        return DEFAULT
    return PALETTES.get(name, DEFAULT)
