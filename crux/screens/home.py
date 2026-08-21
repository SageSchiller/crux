"""The track picker. The root screen, and the only one Esc does not leave.

Three rows, one per track, each carrying what the track is for and how far into
it you are. A track whose engine is not built yet says so on its own row rather
than looking identical to one that works, which is the screen-level expression
of crux D6: never let the student guess which parts are real.
"""

from __future__ import annotations

from ..config import APP_TITLE, CHAIN, SECTIONS, TAGLINE_PARTS, TRACKS
from ..render import Caps, Text, line
from ..session import Session
from . import ListScreen, Screen, push, selector
from .track import TrackScreen


class HomeScreen(ListScreen):
    can_pop = False
    title = APP_TITLE

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    @property
    def status(self) -> str:
        n = len(self.session.state.attempts)
        return f'{n} attempt{"" if n == 1 else "s"}' if n else ''

    def count(self) -> int:
        # The three skill tracks, plus chain when it has content.
        return len(TRACKS) + (1 if self._chain_ready() else 0)

    def _chain_ready(self) -> bool:
        return bool(self.session.registry.track(CHAIN).scenarios)

    def _row_track(self, index: int) -> str:
        return SECTIONS[index] if index < len(SECTIONS) else CHAIN

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        tag = f' {caps.g("bullet")} '.join(TAGLINE_PARTS)
        rows = [line(f'  {tag}', p.muted), Text()]
        if self.session.registry.errors:
            n = len(self.session.registry.errors)
            rows.append(line(f'  {n} content load error(s): press e', p.err))
            rows.append(Text())
        if self.session.state.damaged:
            rows.append(line('  history could not be read, this session '
                             'will not be added to it', p.warn))
            rows.append(Text())
        return rows

    def rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        out: list[Text] = []
        names = list(TRACKS) + ([CHAIN] if self._chain_ready() else [])
        for i, name in enumerate(names):
            track = self.session.registry.track(name)
            sel = i == self.cursor
            t = selector(caps, sel)
            colour = p.accent2 if name == CHAIN else (p.accent if sel else p.fg)
            t.add(f'{name:<9}', colour, bold=sel or name == CHAIN)
            t.add(track.blurb, p.muted)
            out.append(t)

            done, mean = self.session.state.track_summary(name)
            total = len(track.scenarios)
            d = Text().add('     ')
            if name == CHAIN:
                d.add('the capstone: uses all three', p.dim)
                if done:
                    d.add(f'   {done}/{total} run', p.dim)
            elif not track.ready:
                d.add('engine not built yet', p.warn)
            elif done:
                d.add(f'{done}/{total} attempted', p.dim)
                d.add(f'   best mean {mean:.0f}', p.ok if mean >= 70 else p.dim)
            else:
                d.add(f'{total} scenario{"" if total == 1 else "s"}, none '
                      'attempted', p.dim)
            out.append(d)
        return out

    def activate(self, index: int) -> object:
        return push(TrackScreen(self.session, self._row_track(index)))

    def extra_hints(self) -> list[tuple[str, str]]:
        return [('e', 'errors')] if self.session.registry.errors else []

    def handle(self, key):
        if key.name == 'e' and self.session.registry.errors:
            return push(ErrorScreen(self.session))
        return super().handle(key)


class ErrorScreen(Screen):
    """Content that failed to load, shown rather than swallowed."""

    title = 'Content load errors'

    def __init__(self, session: Session) -> None:
        self.session = session

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = [line('  A content file failed to import. The app still runs; '
                     'those scenarios do not.', p.muted), Text()]
        for e in self.session.registry.errors:
            rows.append(line(f'  {e}', p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [('esc', 'back'), ('q', 'quit')]
