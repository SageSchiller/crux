"""The screen a track shows before its engine exists.

It would be easy to leave `salvage` and `conduit` off the picker until Phase 3
and Phase 5. Showing them, clearly labelled as unbuilt, is the better shape for
the same reason crux D6 exists: the app should be legible about what is real,
and that rule has to bind when it is inconvenient or it does not bind at all.

Nothing is recorded here. A `self` tier that quietly wrote a score would be the
exact dishonesty D6 forbids.
"""

from __future__ import annotations

from ..model import Scenario, StubBody
from ..render import Caps, Text, line, wrap_rich
from ..session import Session
from . import ScrollScreen


class StubScreen(ScrollScreen):
    def __init__(self, session: Session, scenario: Scenario) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.body_data: StubBody = scenario.body

    @property
    def title(self) -> str:
        return f'{self.scenario.track}: {self.scenario.title}'

    @property
    def status(self) -> str:
        return self.body_data.phase

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = [line(f'  Not built yet. Lands in {self.body_data.phase}.',
                     p.warn, bold=True), Text()]
        rows.extend(wrap_rich(caps, self.body_data.prompt, caps.cols - 6, '  ',
                              p.fg, p.accent))
        if self.body_data.debrief:
            rows.append(Text())
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))
        if self.scenario.needs:
            rows.append(Text())
            rows.append(line('  needs: ' + ', '.join(self.scenario.needs), p.dim))
        rows.append(Text())
        rows.append(line('  Nothing is scored or recorded on this screen.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'),
                   ('q', 'quit'), ('?', 'help')])
