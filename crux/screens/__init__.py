"""The screen contract, made structural rather than left to discipline.

Four rules. Three of them are cheap to state and easy to erode once there
are three tracks of content pushing on them, so they are enforced here:

1. **Every screen names its own exits.** `hints()` returning nothing raises.
2. **Esc always goes back.** The base handler maps it, and a screen that
   overrides `handle` still falls through to the base for keys it ignores.
3. **No screen is ever blank.** `body()` returning nothing raises.
4. **Nothing needs a key you were never shown.** Solved by construction rather
   than by assertion: `ListScreen` owns both its navigation keys and the hints
   describing them, so the two cannot drift apart.

Screens return `Text`, never strings with escape codes, so `test.py` can render
each one at every rung of the capability ladder and check widths.


**Forked from hone (crux D4).** The contract is proven; the decision
numbers cited are crux's own.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..keys import Key
from ..render import (Caps, Text, box_bottom, box_row, box_sep, box_top,
                      footer, line)

# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

#: Set by the app so any screen can honour the `?` its footer advertises.
#: Held here rather than threaded through every constructor because the base
#: handler is the one place that needs it, and every screen promises the key.
OPEN_HELP = None


def set_help_factory(factory) -> None:
    global OPEN_HELP
    OPEN_HELP = factory


@dataclass(frozen=True, slots=True)
class Action:
    kind: str                       # stay | push | pop | replace | quit
    screen: object | None = None


STAY = Action('stay')
POP = Action('pop')
QUIT = Action('quit')
#: Unwind the whole stack back to the home screen. Esc walks back one level,
#: which is right when you are one level deep and tedious when you are four:
#: lesson inside a tool inside a review. Quitting to escape a menu is the
#: thing this prevents.
ROOT = Action('root')


def push(screen) -> Action:
    return Action('push', screen)


def replace(screen) -> Action:
    return Action('replace', screen)


class ScreenContractError(RuntimeError):
    """A screen broke one of the screen contract rules. Always a bug in the screen."""


# --------------------------------------------------------------------------
# Base screen
# --------------------------------------------------------------------------

class Screen:
    """One full-screen view. Subclasses provide `body()` and `hints()`."""

    #: Shown in the header frame.
    title = ''
    #: Right-aligned in the header frame.
    status = ''
    #: Set by screens that take over the keyboard, so the frame changes (the reserved exit chord).
    capturing = False
    #: Whether Esc leaves this screen. Only the root sets this False.
    can_pop = True

    # -- content -----------------------------------------------------------

    def body(self, caps: Caps) -> list[Text]:
        raise NotImplementedError

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        """Key hints for the footer. Takes caps because hints contain glyphs,
        and a hardcoded arrow would survive into the ASCII rung."""
        raise NotImplementedError

    # -- input -------------------------------------------------------------

    @property
    def escape_key(self) -> str:
        """The key that leaves this screen, in `keys` notation.

        rule 2 says Esc always goes back, and that holds everywhere except
        the one screen where Esc is a legitimate answer: a screen that captures raw keys.
        Rather than carve out an exception the harness has to know about, every
        screen names its own way out and the contract becomes uniform: pressing
        `escape_key` must never leave you where you were. Capture screens
        override this with the reserved exit chord's reserved chord.
        """
        return 'ESC'

    def close(self) -> None:
        """Release anything this screen holds outside the process.

        Called by the app when the screen is popped for any reason and for
        every stacked screen at shutdown. Idempotent by contract. Exists
        because a screen cannot see the `q` that quits the whole app: the
        challenge sandbox used to leak whenever someone quit from inside one.
        """

    def handle(self, key: Key) -> Action:
        """Override for screen-specific keys, then `return super().handle(key)`."""
        name = key.name
        if name == 'ESC':
            # Esc goes back, and at the root there is nowhere back to, so it
            # does nothing. It used to quit, which made the most-pressed key
            # in the app also the one that threw away your session from the
            # one screen you return to most: press it once too often on the
            # way out of a lesson and crux was gone. Nothing is lost by
            # ignoring it, `q` is the advertised way out, and the home footer
            # never offered Esc in the first place, so this takes away a
            # behaviour nobody was told about rather than one anybody used.
            return POP if self.can_pop else STAY
        if name == 'H' and not key.ctrl and not key.alt:
            # Deliberately uppercase. Every lowercase letter is an answer
            # somewhere in this app, and the screens where H would be typed
            # (marking screens, a text prompt) consume their own keys before this
            # is ever reached.
            return ROOT if self.can_pop else STAY
        if name == 'q' and not key.ctrl and not key.alt:
            return QUIT
        # Every footer advertises `?`. It did nothing for the whole build,
        # which is the rule 4 failure the footer contract exists to
        # prevent: a key the student was told about that does not work.
        if name == '?' and OPEN_HELP is not None:
            return push(OPEN_HELP())
        return STAY

    # -- framing -----------------------------------------------------------

    def _checked_hints(self, caps: Caps) -> list[tuple[str, str]]:
        hints = self.hints(caps)
        if not hints:
            raise ScreenContractError(
                f'{type(self).__name__}: the screen contract requires at least one key hint')
        return hints

    def _checked_body(self, caps: Caps) -> list[Text]:
        rows = self.body(caps)
        if not rows:
            raise ScreenContractError(
                f'{type(self).__name__}: the screen contract forbids a blank screen; '
                f'render an explanatory empty state instead')
        return rows

    def render(self, caps: Caps) -> list[Text]:
        """Header frame, body, footer frame. Never overflows `caps.cols`."""
        w = caps.cols
        heavy = self.capturing
        colour = caps.palette.warn if heavy else caps.palette.border

        body = self._checked_body(caps)

        # Hard backstop on height, enforced once here rather than trusted to
        # every screen. Screens window their own content sensibly, but a
        # terminal smaller than the documented minimum must still degrade by
        # truncating rather than by running off the bottom.
        overhead = 4                       # top, divider, footer, bottom
        room = max(1, caps.rows - overhead)
        if len(body) > room:
            body = body[:room]

        out: list[Text] = [
            box_top(caps, w, self.title, self.status, heavy=heavy, color=colour),
        ]
        for row in body:
            out.append(box_row(caps, w, row, heavy=heavy, color=colour))

        # The footer lives inside the frame, below a divider. Closing the box
        # first and then printing the hints underneath left the footer looking
        # detached, as though the screen had ended before it.
        out.append(box_sep(caps, w, heavy=heavy, color=colour))
        f = Text().add(' ')
        f.spans.extend(footer(caps, self._checked_hints(caps)).spans)
        out.append(box_row(caps, w, f, heavy=heavy, color=colour))
        out.append(box_bottom(caps, w, heavy=heavy, color=colour))
        return out


# --------------------------------------------------------------------------
# List screen
# --------------------------------------------------------------------------

class ListScreen(Screen):
    """A cursor over rows, with navigation and its own hints kept in one place.

    This is rule 4 solved structurally: the keys this responds to and the
    footer describing them are produced by the same code, so no screen can ship
    a shortcut the student was never told about.
    """

    def __init__(self) -> None:
        self.cursor = 0
        self.scroll = 0

    # -- to implement ------------------------------------------------------

    def rows(self, caps: Caps) -> list[Text]:
        """One Text per selectable row, already styled for the cursor."""
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def activate(self, index: int) -> Action:
        return STAY

    def extra_hints(self) -> list[tuple[str, str]]:
        return []

    def empty_state(self, caps: Caps) -> list[Text]:
        """Shown when there is nothing to list. Never allowed to be blank."""
        return [line('Nothing here yet.', caps.palette.muted)]

    def header_rows(self, caps: Caps) -> list[Text]:
        """Non-selectable lines above the list. Rendered in both states.

        Kept separate from `rows()` so the cursor index always matches the item
        index, which is what stops off-by-one bugs when a screen grows a banner.
        """
        return []

    # -- provided ----------------------------------------------------------

    def nav_glyphs(self, caps: Caps) -> tuple[str, str]:
        return caps.g('up') + caps.g('down'), caps.g('enter')

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        """Navigation, then the screen's own keys, then the universal exits.

        Every entry here is a key the screen genuinely responds to. That is the screen contract
        rule 4, and keeping the list next to the handler is what stops the two
        drifting apart as screens grow.
        """
        up_down, enter = self.nav_glyphs(caps)
        out = [(up_down, 'move'), (enter, 'select')] + self.extra_hints()
        if self.can_pop:
            out.append(('esc', 'back'))
            out.append(('H', 'home'))
        out.append(('q', 'quit'))
        out.append(('?', 'help'))
        return out

    def clamp(self) -> None:
        n = self.count()
        self.cursor = 0 if n <= 0 else max(0, min(self.cursor, n - 1))

    def viewport(self, caps: Caps, used: int) -> int:
        """Rows available for the list after the frame, header and footer."""
        return max(3, caps.rows - 4 - used)

    def body(self, caps: Caps) -> list[Text]:
        """Header, then as much of the list as fits, windowed on the cursor.

        Without the windowing a track with thirty-seven scenarios renders
        thirty-seven rows and runs straight off the bottom of the terminal.
        A track will have more scenarios than a small terminal has lines, so
        this is not an edge case.
        """
        self.clamp()
        head = self.header_rows(caps)
        if self.count() <= 0:
            return head + self.empty_state(caps)

        rows = self.rows(caps)
        vp = self.viewport(caps, len(head))
        if len(rows) <= vp:
            self.scroll = 0
            return head + rows

        # Keep the cursor in view. Rows and items are one-to-one on most
        # screens; where a screen adds a detail row the drift is one line and
        # the clamping below absorbs it.
        vp -= 1                                    # room for the indicator
        self.scroll = max(0, min(self.scroll, len(rows) - vp))
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vp:
            self.scroll = self.cursor - vp + 1
        self.scroll = max(0, min(self.scroll, max(0, len(rows) - vp)))

        window = rows[self.scroll:self.scroll + vp]
        p = caps.palette
        above, below = self.scroll, max(0, len(rows) - self.scroll - vp)
        marker = Text().add('  ', p.dim)
        if above:
            marker.add(f'{caps.g("up")} {above} above   ', p.dim)
        if below:
            marker.add(f'{caps.g("down")} {below} below', p.dim)
        if not above and not below:
            marker.add(' ', p.dim)
        return head + window + [marker]

    def handle(self, key: Key) -> Action:
        n = self.count()
        name = key.name
        if n > 0:
            if name in ('Down', 'j') and not key.ctrl:
                self.cursor = (self.cursor + 1) % n
                return STAY
            if name in ('Up', 'k') and not key.ctrl:
                self.cursor = (self.cursor - 1) % n
                return STAY
            if name == 'Home':
                self.cursor = 0
                return STAY
            if name == 'End':
                self.cursor = n - 1
                return STAY
            if name == 'PgDn':
                self.cursor = min(n - 1, self.cursor + 10)
                return STAY
            if name == 'PgUp':
                self.cursor = max(0, self.cursor - 10)
                return STAY
            # Right is deliberately not an activate key: screens that hold tabs
            # use it to move between them, and a key that means 'open' on one
            # screen and 'next view' on another is exactly the inconsistency
            # rule 4 is trying to prevent.
            if name in ('RET', 'l'):
                return self.activate(self.cursor)
            if name.isdigit() and name != '0':
                idx = int(name) - 1
                if idx < n:
                    self.cursor = idx
                    return self.activate(idx)
                return STAY
        return super().handle(key)


def selector(caps: Caps, selected: bool) -> Text:
    """The cursor marker, sized the same whether or not it is showing."""
    g = caps.g('sel')
    return (Text().add(f' {g} ', caps.palette.accent) if selected
            else Text().add('   '))
