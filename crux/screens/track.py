"""One track's scenarios.

Each row carries the tier badge, because crux D6 says the three tiers are never
blurred and a list is exactly where blurring happens: `verified` and `self`
render identically unless something on the row says otherwise.
"""

from __future__ import annotations

from ..model import ConduitBody, SalvageBody, StubBody
from ..render import Caps, Text, line
from ..session import Session
from . import ListScreen, push, selector

TIER_MARK = {'verified': 'verified', 'graded': 'graded', 'self': 'self-marked'}


class TrackScreen(ListScreen):
    def __init__(self, session: Session, track_name: str) -> None:
        super().__init__()
        self.session = session
        self.track_name = track_name
        self.track = session.registry.track(track_name)

    @property
    def title(self) -> str:
        return self.track_name

    @property
    def status(self) -> str:
        return self.track.blurb

    def count(self) -> int:
        return len(self.track.scenarios)

    def empty_state(self, caps: Caps) -> list[Text]:
        return [line('  No scenarios in this track yet.', caps.palette.muted)]

    def rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        out: list[Text] = []
        for i, s in enumerate(self.track.scenarios):
            sel = i == self.cursor
            t = selector(caps, sel)
            best = self.session.state.best(s.id)
            if best is None:
                mark = caps.g('dot_off')
                colour = p.dim
            elif best.total >= 90:
                mark = caps.g('check')
                colour = p.ok
            else:
                mark = caps.g('dot_on')
                colour = p.warn
            t.add(f'{mark} ', colour)
            t.add(s.title, p.accent if sel else p.fg, bold=sel)
            out.append(t)

            d = Text().add('       ')
            tier = TIER_MARK.get(s.tier, s.tier)
            d.add(tier, p.ok if s.tier == 'verified' else
                        (p.info if s.tier == 'graded' else p.warn))
            if isinstance(s.body, StubBody):
                d.add(f'   {s.body.phase}', p.dim)
            if best is not None:
                d.add(f'   best {best.total:.0f}', p.dim)
            out.append(d)
        return out

    def activate(self, index: int) -> object:
        from .mark import MarkScreen
        from .salvage import SalvageScreen
        from .stub import StubScreen
        s = self.track.scenarios[index]
        if isinstance(s.body, StubBody):
            return push(StubScreen(self.session, s))
        if isinstance(s.body, SalvageBody):
            return push(SalvageScreen(self.session, s))
        if isinstance(s.body, ConduitBody):
            from .conduit import ConduitScreen
            return push(ConduitScreen(self.session, s))
        return push(MarkScreen(self.session, s))
