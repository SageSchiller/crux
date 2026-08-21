"""The result screen, and the one number nobody has ever been shown.

Everyone finishes a box knowing what they failed to find. Almost nobody has
ever seen a count of **what they went after that was never going to pay**, and
that number is the whole argument of crux D8. So `chased` renders at the same
weight as `missed`, with the actual line text beside it, and the decoys are
named as decoys: a rabbit hole you can see the shape of afterwards is one you
recognise the next time it is dressed differently.
"""

from __future__ import annotations

from ..clock import fmt
from ..model import MarkBody, Scenario
from ..provenance import based_on
from ..render import Caps, Text, bar, line, wrap_rich
from ..scoring import Score
from ..session import Session
from . import POP, ScrollScreen


class ResultScreen(ScrollScreen):
    def __init__(self, session: Session, scenario: Scenario, score: Score,
                 lines, chose=None) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.score = score
        #: The screen as it was actually built for this attempt. Held rather
        #: than rebuilt, because a result that rendered a different seed's
        #: lines than the ones you marked would be worse than no result.
        self.lines = lines
        self.chose = chose
        self.body_data: MarkBody = scenario.body

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        return f'{self.score.total:.0f}  {self.score.band}'

    def _text_for(self, line_id: str) -> str:
        for ln in self.lines:
            if ln.id == line_id:
                return ln.text or '(blank line)'
        return line_id

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.score
        rows: list[Text] = []

        head = Text().add('  ')
        head.spans.extend(bar(caps, s.total / 100.0, 20).spans)
        head.add(f'  {s.total:.0f}', p.ok if s.total >= 70 else p.warn, bold=True)
        head.add(f'  {s.summary()}', p.muted)
        rows.append(head)

        detail = Text().add('  ')
        detail.add(f'recall {s.recall:.0%}', p.dim)
        detail.add(f'   precision {s.precision:.0%}', p.dim)
        detail.add(f'   {fmt(s.elapsed)}', p.dim)
        rows.append(detail)
        rows.append(Text())

        for label, ids, colour in (
            ('missed', s.missed, p.err),
            ('chased', s.chased, p.warn),
        ):
            for i, lid in enumerate(ids):
                t = Text().add('  ')
                t.add(f'{label if i == 0 else "":<7}', colour, bold=(i == 0))
                is_decoy = lid in s.chased_decoys
                t.add(self._text_for(lid), p.fg)
                if is_decoy:
                    t.add('   (authored to tempt)', p.dim)
                rows.append(t)
        if s.clean_pass:
            rows.append(line('  clean pass: found everything, chased nothing.',
                             p.ok))
        rows.append(Text())

        if self.chose is not None:
            colour = p.ok if self.chose.correct else p.err
            rows.append(line(f'  {caps.g("arrow")} {self.chose.text}', colour))
            if self.chose.why:
                rows.extend(wrap_rich(caps, self.chose.why, caps.cols - 8,
                                      '     ', p.muted, p.accent))
            rows.append(Text())

        if self.body_data.debrief:
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))

        label = based_on(self.scenario.source)
        if label or self.scenario.waypoint:
            rows.append(Text())
        if label:
            rows.append(line(f'  based on {label}', p.info))
        if self.scenario.waypoint:
            rows.append(line(f'  Waypoint node: {self.scenario.waypoint}', p.dim))
        if self.session.save_error:
            rows.append(line(f'  history not saved: {self.session.save_error}',
                             p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'),
                   ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
