"""The result of a salvage attempt.

Shows the requirement list with what the closest request actually met, because
the useful thing after a failed exploit is not a score, it is a checklist with
one line ticked differently from what you expected.
"""

from __future__ import annotations

from ..clock import fmt
from ..model import SalvageBody, Scenario
from ..render import Caps, Text, line, wrap_rich
from ..session import Session
from . import POP, Screen


class RunResultScreen(Screen):
    def __init__(self, session: Session, scenario: Scenario, score,
                 record) -> None:
        self.session = session
        self.scenario = scenario
        self.score = score
        self.record = record
        self.body_data: SalvageBody = scenario.body

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        return 'landed' if self.score.landed else 'did not land'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.score
        rows: list[Text] = []

        head = Text().add('  ')
        head.add('LANDED' if s.landed else 'NO', p.ok if s.landed else p.err,
                 bold=True)
        head.add(f'   {s.summary()}', p.muted)
        head.add(f'   {fmt(s.elapsed)}', p.dim)
        rows.append(head)
        rows.append(Text())

        best = self.record.closest()
        met = set(self.record.met(best)) if best else set()
        for q in self.record.requirements:
            ok = q in met
            t = Text().add('  ')
            t.add(caps.g('check') if ok else caps.g('cross'),
                  p.ok if ok else p.err)
            t.add(f' {q.name}', p.fg if ok else p.muted)
            if not ok and q.hint:
                t.add(f'   {q.hint}', p.dim)
            rows.append(t)
        rows.append(Text())

        if s.read_first is False:
            rows.extend(wrap_rich(
                caps,
                '**You ran it before you opened it.** Nothing came of it this '
                'time. It is recorded, and it is the subject of the last '
                'scenario in this track.',
                caps.cols - 6, '  ', p.warn, p.accent))
            rows.append(Text())

        if self.body_data.defects:
            rows.append(line('  defects in the original: '
                             + ', '.join(self.body_data.defects), p.dim))
        if self.body_data.debrief:
            rows.append(Text())
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')]

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
