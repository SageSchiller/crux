"""Key representation, notation, and terminal input decoding.

Two jobs, deliberately kept in one place because they must agree exactly:

1. The **notation** content is authored in (`C-b`, `SPC`, `M-x`, `"`), parsed to
   `Key` objects and rendered back. `test.py` round-trips this per Phase 0.
2. The **decoder** that turns raw terminal bytes into the same `Key` objects,
   using the Kitty keyboard protocol when the terminal supports it and falling
   back to legacy decoding when it does not (unambiguous key decoding).

Unambiguous decoding is needed because legacy terminal encoding cannot tell
`Ctrl+I` from `Tab`, `Ctrl+M` from `Enter`, or `Ctrl+[` from `Escape`: they are
the same byte. `AMBIGUOUS_LEGACY` names every such collision so a drill can say
"your terminal cannot express this" rather than silently marking a correct
answer wrong.

No terminal is touched here. Enabling the protocol lives in `term.py`; this
module only understands the bytes that result.


**Forked from hone (crux D4), deliberately, not shared.** Fixes here do not
flow back and are not expected to. Decision numbers below are crux's own;
where hone's plan is cited it is named as hone's.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# Key model
# --------------------------------------------------------------------------

#: Named keys. A `Key.name` is either one of these or a single printable char.
SPECIALS = (
    'SPC', 'RET', 'TAB', 'ESC', 'BSP', 'DEL',
    'Up', 'Down', 'Left', 'Right', 'Home', 'End', 'PgUp', 'PgDn', 'Ins',
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
)

#: US-layout shifted forms. Lets content write `"` or `S-'` interchangeably;
#: parsing normalises the second into the first so `accepts` lists behave.
SHIFTED = {
    '`': '~', '1': '!', '2': '@', '3': '#', '4': '$', '5': '%', '6': '^',
    '7': '&', '8': '*', '9': '(', '0': ')', '-': '_', '=': '+',
    '[': '{', ']': '}', '\\': '|', ';': ':', "'": '"', ',': '<', '.': '>',
    '/': '?',
}
SHIFTED.update({c: c.upper() for c in 'abcdefghijklmnopqrstuvwxyz'})

#: Collisions legacy decoding cannot resolve. Maps the byte's canonical
#: meaning to the chord it is indistinguishable from. Surfaced by the drill
#: engine when the Kitty protocol is unavailable.
AMBIGUOUS_LEGACY = {
    'TAB': 'C-i',
    'RET': 'C-m',
    'ESC': 'C-[',
    'BSP': 'C-h',
}


class KeyError_(ValueError):
    """Raised when a key string cannot be parsed. Content bugs, not input bugs."""


@dataclass(frozen=True, slots=True)
class Key:
    """One keypress. `name` is a single printable char or a member of SPECIALS."""

    name: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False

    def __str__(self) -> str:
        return unparse(self)


# --------------------------------------------------------------------------
# Notation
# --------------------------------------------------------------------------

def parse(s: str) -> Key:
    """Parse one key in `C-`/`M-`/`S-` notation.

    `S-` on a printable character normalises to that character's shifted form,
    so `S-'` and `"` produce the same Key. `S-` on a named key is kept as a
    modifier, because `S-TAB` has no shifted character to fold into.
    """
    if not s:
        raise KeyError_('empty key string')

    ctrl = alt = shift = False
    rest = s
    # Modifiers may appear in any order; the canonical output order is C- M- S-.
    while len(rest) > 2 and rest[1] == '-' and rest[0] in 'CMS':
        flag, rest = rest[0], rest[2:]
        if flag == 'C':
            ctrl = True
        elif flag == 'M':
            alt = True
        else:
            shift = True

    if rest in SPECIALS:
        return Key(rest, ctrl, alt, shift)
    if len(rest) != 1:
        raise KeyError_(f'not a key: {s!r}')
    if shift:
        # Fold shift into the character where a shifted form exists.
        if rest in SHIFTED:
            return Key(SHIFTED[rest], ctrl, alt, False)
        return Key(rest, ctrl, alt, True)
    return Key(rest, ctrl, alt, False)


def unparse(k: Key) -> str:
    """Render a Key back to notation. `parse(unparse(k)) == k` for every Key."""
    out = ''
    if k.ctrl:
        out += 'C-'
    if k.alt:
        out += 'M-'
    if k.shift:
        out += 'S-'
    return out + k.name


def parse_seq(seq) -> list[Key]:
    """Parse a content-authored sequence such as `['C-b', '"']`."""
    if isinstance(seq, str):
        raise KeyError_('sequences are lists of key strings, not one string')
    return [parse(s) for s in seq]


def unparse_seq(keys) -> list[str]:
    return [unparse(k) for k in keys]


def describe(seq) -> str:
    """Human-readable form for banners and hints: `C-b "`."""
    return ' '.join(unparse_seq(seq))


# --------------------------------------------------------------------------
# Decoding
# --------------------------------------------------------------------------

_C0_NAMES = {0x09: 'TAB', 0x0D: 'RET', 0x1B: 'ESC', 0x08: 'BSP'}

_CSI_FINAL_KEYS = {
    'A': 'Up', 'B': 'Down', 'C': 'Right', 'D': 'Left',
    'H': 'Home', 'F': 'End',
    'P': 'F1', 'Q': 'F2', 'R': 'F3', 'S': 'F4',
}

_CSI_TILDE_KEYS = {
    1: 'Home', 2: 'Ins', 3: 'DEL', 4: 'End', 5: 'PgUp', 6: 'PgDn',
    15: 'F5', 17: 'F6', 18: 'F7', 19: 'F8', 20: 'F9', 21: 'F10',
    23: 'F11', 24: 'F12',
}

#: Kitty reports these as their unicode codepoints rather than as characters.
_KITTY_CODE_KEYS = {
    9: 'TAB', 13: 'RET', 27: 'ESC', 32: 'SPC', 127: 'BSP',
    57414: 'RET', 57409: 'TAB',  # keypad/alternate reports seen in the wild
}


def _mods(n: int) -> tuple[bool, bool, bool]:
    """Decode a CSI modifier parameter into (ctrl, alt, shift).

    The wire value is 1 + a bitmask, so an absent parameter and an unmodified
    key both mean 'no modifiers'.
    """
    if n <= 1:
        return False, False, False
    bits = n - 1
    return bool(bits & 4), bool(bits & 2), bool(bits & 1)


def _from_c0(b: int) -> Key:
    """Decode a legacy control byte.

    The collisions in `AMBIGUOUS_LEGACY` resolve to the *named* key here, which
    is the more common intent. A drill wanting the other reading has to say so.
    """
    if b in _C0_NAMES:
        return Key(_C0_NAMES[b])
    if b == 0x00:
        return Key('SPC', ctrl=True)
    # Space is `SPC`, not a bare ' '. **Diverged from hone here (crux D4).**
    # This module promises that the decoder produces "the same Key objects"
    # the notation parses to, and for exactly one byte it did not: `C-SPC`
    # already decoded to Key('SPC', ctrl=True) while a plain space decoded to
    # Key(' '), so the chord and its unmodified form had different base names.
    # Every screen comparing against parse('SPC') silently never matched. A
    # unit test could not catch it, because a test that builds its input with
    # parse() is asking the notation whether it agrees with itself; it took
    # driving the real app through a pty. `test.py` now asserts agreement
    # across every special key permanently.
    if b == 0x20:
        return Key('SPC')
    if 0x01 <= b <= 0x1A:
        return Key(chr(b + 0x60), ctrl=True)
    if 0x1C <= b <= 0x1F:
        return Key({0x1C: '\\', 0x1D: ']', 0x1E: '^', 0x1F: '_'}[b], ctrl=True)
    if b == 0x7F:
        return Key('BSP')
    return Key(chr(b))


class Decoder:
    """Incremental byte-stream decoder. Feed it whatever `read()` returned.

    Holds partial escape sequences between calls. A lone `ESC` at the end of the
    buffer is genuinely ambiguous (it may begin a sequence that has not arrived
    yet), so it is held back until `flush()` decides no more is coming. The read
    loop calls `flush()` after a short timeout.
    """

    def __init__(self, kitty: bool = False) -> None:
        self.kitty = kitty
        self.buf = bytearray()

    def feed(self, data: bytes) -> list[Key]:
        self.buf.extend(data)
        return self._drain(final=False)

    def flush(self) -> list[Key]:
        """Resolve anything held back, including a lone trailing ESC."""
        return self._drain(final=True)

    def _drain(self, final: bool) -> list[Key]:
        out: list[Key] = []
        while self.buf:
            key, used = self._consume(final)
            if used == 0:
                break
            del self.buf[:used]
            if key is not None:
                out.append(key)
        return out

    def _consume(self, final: bool) -> tuple[Key | None, int]:
        """Try to take one key off the front. Returns (key, bytes consumed).

        A `used` of 0 means 'incomplete, wait for more bytes'.
        """
        b = self.buf[0]

        if b != 0x1B:
            if b < 0x80:
                return _from_c0(b), 1
            return self._consume_utf8()

        # ESC: alone, or the start of something longer.
        if len(self.buf) == 1:
            return (Key('ESC'), 1) if final else (None, 0)

        nxt = self.buf[1]
        if nxt == ord('['):
            return self._consume_csi(final)
        if nxt == ord('O'):
            if len(self.buf) < 3:
                return (Key('ESC'), 1) if final else (None, 0)
            name = _CSI_FINAL_KEYS.get(chr(self.buf[2]))
            return (Key(name), 3) if name else (Key('ESC'), 1)

        # ESC followed by anything else is Alt+that key. Decode the tail with
        # a throwaway decoder so multi-byte tails (UTF-8, another escape
        # sequence) are handled by one code path. Fed one byte at a time,
        # stopping at the first key: feeding the whole tail at once decoded
        # everything behind the Alt chord too and then counted all of it as
        # consumed, so `ESC a b` in one read emitted M-a and swallowed b.
        tail = bytes(self.buf[1:])
        inner = Decoder(kitty=self.kitty)
        keys: list[Key] = []
        fed = 0
        for fed in range(1, len(tail) + 1):
            keys = inner.feed(tail[fed - 1:fed])
            if keys:
                break
        if not keys and final:
            keys = inner.flush()
        if not keys:
            return (None, 0)
        k = keys[0]
        used = 1 + fed - len(inner.buf)
        return Key(k.name, k.ctrl, True, k.shift), used

    def _consume_utf8(self) -> tuple[Key | None, int]:
        b = self.buf[0]
        width = 2 if b >= 0xC0 else 1
        if b >= 0xE0:
            width = 3
        if b >= 0xF0:
            width = 4
        if len(self.buf) < width:
            return (None, 0)
        try:
            ch = bytes(self.buf[:width]).decode('utf-8')
        except UnicodeDecodeError:
            return (None, 1)  # drop the bad byte rather than wedging
        return Key(ch), width

    def _consume_csi(self, final: bool) -> tuple[Key | None, int]:
        # CSI = ESC [ params intermediates final, final in 0x40..0x7E.
        i = 2
        while i < len(self.buf) and 0x20 <= self.buf[i] <= 0x3F:
            i += 1
        while i < len(self.buf) and 0x20 <= self.buf[i] <= 0x2F:
            i += 1
        if i >= len(self.buf):
            return (Key('ESC'), 1) if final else (None, 0)

        fin = chr(self.buf[i])
        params = bytes(self.buf[2:i]).decode('ascii', 'replace')
        used = i + 1
        nums = []
        for part in params.split(';'):
            head = part.split(':')[0]
            nums.append(int(head) if head.isdigit() else 0)

        if fin == 'u':
            code = nums[0] if nums else 0
            ctrl, alt, shift = _mods(nums[1] if len(nums) > 1 else 1)
            return self._kitty_key(code, ctrl, alt, shift), used

        if fin == '~':
            name = _CSI_TILDE_KEYS.get(nums[0] if nums else 0)
            ctrl, alt, shift = _mods(nums[1] if len(nums) > 1 else 1)
            return (Key(name, ctrl, alt, shift), used) if name else (None, used)

        if fin in _CSI_FINAL_KEYS:
            ctrl, alt, shift = _mods(nums[1] if len(nums) > 1 else 1)
            return Key(_CSI_FINAL_KEYS[fin], ctrl, alt, shift), used

        return (None, used)  # unknown sequence: swallow rather than emit noise

    @staticmethod
    def _kitty_key(code: int, ctrl: bool, alt: bool, shift: bool) -> Key | None:
        """Build a Key from a Kitty `CSI code ; mods u` report.

        This is the whole payoff of unambiguous key decoding: the base key arrives as its own
        codepoint, so `Ctrl+I` is code 105 with ctrl set and `Tab` is code 9,
        and the two stop being the same thing.
        """
        if code in _KITTY_CODE_KEYS:
            return Key(_KITTY_CODE_KEYS[code], ctrl, alt, shift)
        if code <= 0:
            return None
        try:
            ch = chr(code)
        except ValueError:
            return None
        if shift and ch in SHIFTED:
            return Key(SHIFTED[ch], ctrl, alt, False)
        return Key(ch, ctrl, alt, shift)


def ambiguity_for(seq) -> list[str]:
    """Which keys in this sequence a legacy terminal cannot express.

    Returns notation strings, so the drill can print exactly what is at risk.
    """
    out = []
    for k in seq:
        s = unparse(k)
        for named, chord in AMBIGUOUS_LEGACY.items():
            if s == chord:
                out.append(f'{chord} (indistinguishable from {named})')
    return out
