"""The sift result: what you got right, what you got wrong, and why each.

**The screen this replaced said too little.** It printed a score, a bare
`missed` line and a bare `chased` line, and left the student to work out for
themselves why the line they skipped was the lead and why the one they went
after was a trap. That is the entire lesson of the track, and it was the one
thing the screen did not say.

So the result is now a marked-up copy of the key. Every line that mattered
appears under a heading that names the verdict on it, with a sentence saying
what that line meant. Three headings, in the order they teach:

* **What mattered** comes first, found or missed, because the lead is the
  point of the exercise whether or not you saw it.
* **What you chased** is second, because the count nobody is ever shown about
  themselves is how much they went after that was never going to pay.
* **What you left alone** is last and only appears when there was a decoy you
  did not take, because correctly ignoring a tempting line is a real skill and
  silence is a poor way to acknowledge it.

The headline is a sentence rather than a band name. "0 lost" tells you nothing
you can act on; "you missed the way in" does.
"""

from __future__ import annotations

from ..clock import fmt
from ..model import MarkBody, Scenario
from ..provenance import based_on
from ..render import Caps, Text, bar, line, wrap_rich
from ..scoring import Score
from ..session import Session
from . import POP, ScrollScreen


def _verdict(score: Score) -> str:
    """One sentence naming the outcome, in the words a person would use."""
    missed, chased = len(score.missed), len(score.chased)
    found, total = len(score.found), len(score.found) + missed
    if score.no_lead:
        if not chased:
            return 'Correct: there was nothing here to act on.'
        return (f'There was nothing here to act on, and you went after '
                f'{chased}.')
    if not missed and not chased:
        return 'You found everything that mattered and chased nothing.'
    if not missed:
        return (f'You found everything that mattered, and went after {chased} '
                f'that would not have paid.')
    if found == 0 and chased:
        return f'You missed the way in, and went after {chased} that was not it.'
    if found == 0:
        return 'You missed the way in.'
    return (f'You found {found} of {total}, and missed {missed}.'
            if not chased else
            f'You found {found} of {total}, missed {missed}, and chased '
            f'{chased}.')


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

    def _line(self, line_id: str):
        for ln in self.lines:
            if ln.id == line_id:
                return ln
        return None

    def _entry(self, caps: Caps, line_id: str, mark: str, mark_colour,
               verdict: str, verdict_colour) -> list[Text]:
        """One key line: its text, then the verdict and what it meant."""
        p = caps.palette
        ln = self._line(line_id)
        text = (ln.text if ln else line_id) or '(a blank line)'
        rows = [Text().add('  ').add(mark, mark_colour)
                .add(' ' + text.strip(), p.fg)]
        note = f'**{verdict}** {ln.why}' if (ln and ln.why) else f'**{verdict}**'
        rows.extend(wrap_rich(caps, note, caps.cols - 10, '      ',
                              p.muted, p.accent))
        return rows

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.score
        rows: list[Text] = []

        head = Text().add('  ')
        head.spans.extend(bar(caps, s.total / 100.0, 18).spans)
        head.add(f'  {s.total:.0f}', p.ok if s.total >= 70 else p.warn,
                 bold=True)
        head.add(f'   {fmt(s.elapsed)}', p.dim)
        rows.append(head)
        rows.extend(wrap_rich(caps, _verdict(s), caps.cols - 6, '  ',
                              p.ok if s.clean_pass else p.warn, p.accent))
        rows.append(Text())

        # What mattered: every lead, found or missed.
        if s.found or s.missed:
            rows.append(line('  What mattered', p.accent, bold=True))
            for lid in s.found:
                rows.extend(self._entry(caps, lid, caps.g('check'), p.ok,
                                        'You marked this.', p.ok))
            for lid in s.missed:
                rows.extend(self._entry(caps, lid, caps.g('cross'), p.err,
                                        'You missed this.', p.err))
            rows.append(Text())

        # What you chased: the count nobody is ever shown about themselves.
        if s.chased:
            rows.append(line('  What you chased', p.warn, bold=True))
            for lid in s.chased_decoys:
                rows.extend(self._entry(caps, lid, caps.g('cross'), p.err,
                                        'A decoy, authored to tempt.', p.warn))
            for lid in s.chased_noise:
                rows.extend(self._entry(caps, lid, caps.g('cross'), p.err,
                                        'Noise. Nothing here to act on.',
                                        p.warn))
            rows.append(Text())

        # Decoys you were offered and did not take.
        avoided = [d for d in sorted(self.body_key_decoys())
                   if d not in s.chased_decoys]
        if avoided:
            rows.append(line('  What you left alone, correctly',
                             p.accent2, bold=True))
            for lid in avoided:
                rows.extend(self._entry(caps, lid, caps.g('check'), p.ok,
                                        'A decoy you did not take.', p.ok))
            rows.append(Text())

        if self.chose is not None:
            colour = p.ok if self.chose.correct else p.err
            rows.append(line('  What you decided to do', p.accent, bold=True))
            rows.append(Text().add('  ')
                        .add(caps.g('check') if self.chose.correct
                             else caps.g('cross'), colour)
                        .add(' ' + self.chose.text, p.fg))
            if self.chose.why:
                rows.extend(wrap_rich(caps, self.chose.why, caps.cols - 10,
                                      '      ', p.muted, p.accent))
            rows.append(Text())

        if self.body_data.debrief:
            rows.append(line('  The habit', p.accent, bold=True))
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))

        label = based_on(self.scenario.source)
        if label or self.scenario.waypoint:
            rows.append(Text())
        if label:
            rows.append(line(f'  based on {label}', p.info))
        if self.scenario.waypoint:
            rows.append(line(f'  Waypoint node: {self.scenario.waypoint}',
                             p.dim))
        if self.session.save_error:
            rows.append(line(f'  history not saved: {self.session.save_error}',
                             p.err))
        return rows

    def body_key_decoys(self) -> frozenset[str]:
        return frozenset(l.id for l in self.lines if l.kind == 'decoy')

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
