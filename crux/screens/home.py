"""The track picker. The root screen, and the only one Esc does not leave.

Three rows, one per track, each carrying what the track is for and how far into
it you are. A track whose engine is not built yet says so on its own row rather
than looking identical to one that works, which is the screen-level expression
of crux D6: never let the student guess which parts are real.
"""

from __future__ import annotations

from ..config import (APP_TITLE, CHAIN, COMPOSITE, PROCTOR, TAGLINE_PARTS,
                      TRACKS)
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

    def _names(self) -> list[str]:
        """The rows, in order: every skill track, then every composite that
        has content.

        Built in one place rather than derived from `SECTIONS` by index,
        because a composite with no scenarios is not shown and an index into
        `SECTIONS` then names the wrong track. That was survivable while
        `chain` was the only composite; with two of them it is a bug waiting
        for the first empty one.
        """
        return list(TRACKS) + [n for n in COMPOSITE
                               if self.session.registry.track(n).scenarios]

    def count(self) -> int:
        return len(self._names())

    def _row_track(self, index: int) -> str:
        names = self._names()
        return names[index] if index < len(names) else names[-1]

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

    def blocks(self, caps: Caps) -> list[list[Text]]:
        p = caps.palette
        out: list[list[Text]] = []
        for i, name in enumerate(self._names()):
            track = self.session.registry.track(name)
            sel = i == self.cursor
            t = selector(caps, sel)
            composite = name in COMPOSITE
            colour = p.accent2 if composite else (p.accent if sel else p.fg)
            t.add(f'{name:<9}', colour, bold=sel or composite)
            t.add(track.blurb, p.muted)

            done, mean = self.session.state.track_summary(name)
            total = len(track.scenarios)
            d = Text().add('     ')
            if name == CHAIN:
                d.add('the capstone: uses all three', p.dim)
                if done:
                    d.add(f'   {done}/{total} run', p.dim)
            elif name == PROCTOR:
                d.add('timed: schedules what you have not played', p.dim)
                if done:
                    d.add(f'   {done}/{total} sat', p.dim)
            elif not track.ready:
                d.add('engine not built yet', p.warn)
            elif done:
                d.add(f'{done}/{total} attempted', p.dim)
                d.add(f'   best mean {mean:.0f}', p.ok if mean >= 70 else p.dim)
            else:
                d.add(f'{total} scenario{"" if total == 1 else "s"}, none '
                      'attempted', p.dim)
            out.append([t, d])
        return out

    def activate(self, index: int) -> object:
        return push(TrackScreen(self.session, self._row_track(index)))

    def extra_hints(self) -> list[tuple[str, str]]:
        out = [('e', 'errors')] if self.session.registry.errors else []
        # Uppercase deliberately: every lowercase key on this screen selects
        # something, and a destructive action should not sit one fat-finger
        # away from one of them.
        return out + [('R', 'reset')]

    def handle(self, key):
        if key.name == 'e' and self.session.registry.errors:
            return push(ErrorScreen(self.session))
        if key.name == 'R' and not key.ctrl:
            from .reset import ResetScreen
            return push(ResetScreen(self.session))
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
