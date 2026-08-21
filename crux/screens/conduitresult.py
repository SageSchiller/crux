"""The result of a conduit attempt: which hops answered, and from where."""

from __future__ import annotations

from ..clock import fmt
from ..model import ConduitBody, Scenario
from ..render import Caps, Text, line, wrap_rich
from ..session import Session
from . import POP, ScrollScreen


class ConduitResultScreen(ScrollScreen):
    def __init__(self, session: Session, scenario: Scenario, score,
                 attempt) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.score = score
        self.attempt = attempt
        self.body_data: ConduitBody = scenario.body

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        return 'path open' if self.score.landed else 'no route'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.score
        rows: list[Text] = []
        head = Text().add('  ')
        head.add('OPEN' if s.landed else 'NO ROUTE',
                 p.ok if s.landed else p.err, bold=True)
        head.add(f'   {s.summary()}', p.muted)
        head.add(f'   {fmt(s.elapsed)}', p.dim)
        rows.append(head)
        rows.append(Text())

        for pr in (self.attempt.probes if self.attempt else ()):
            mark = caps.g('check') if pr['ok'] else caps.g('cross')
            row = Text().add('  ')
            row.add(mark, p.ok if pr['ok'] else p.err)
            row.add(f" {pr['name']}", p.fg)
            row.add(f"   from {pr['from']}", p.dim)
            if not pr['ok'] and pr.get('got'):
                row.add(f"   {pr['got'][:24]}", p.warn)
            rows.append(row)

        if self.attempt is not None and self.attempt.error:
            rows.append(Text())
            rows.append(line(f'  {self.attempt.error}', p.err))
        if self.body_data.debrief:
            rows.append(Text())
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
