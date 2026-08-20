"""The sift marking screen: beat one, spot it.

**Why marking lines rather than typing an answer or picking from a list.** Free
text has to be graded by pattern, which turns the drill into a guessing game
about phrasing. Multiple choice pre-filters the noise, which deletes the entire
skill being trained. Marking lines is what you physically do when you read a
scan, and it grades exactly.

Space toggles, Enter submits. That is the checkbox idiom every multi-select
already uses, and submitting with nothing marked is a real answer rather than
an empty one: on a crux D9 scenario it is the correct one.
"""

from __future__ import annotations

from ..clock import Stopwatch
from ..model import MarkBody, Scenario
from ..render import Caps, Text, line, wrap_rich
from ..scoring import score_marks
from ..session import Session
from . import ListScreen, STAY, push, replace, selector


class MarkScreen(ListScreen):
    """A screen of output, and a cursor that marks what mattered."""

    def __init__(self, session: Session, scenario: Scenario) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.body_data: MarkBody = scenario.body
        self.marked: set[str] = set()
        self.watch = Stopwatch(session.clock)
        self.watch.start()
        #: Set when the watch is handed to the act beat. Without it, `close`
        #: pauses a watch this screen no longer owns and beat two's time
        #: silently vanishes from history, which is the one thing crux D12
        #: cannot tolerate: elapsed time is a scored quantity, and `proctor`
        #: is going to be built on exactly these numbers.
        self._handed_off = False

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        n = len(self.marked)
        return f'{n} marked' if n else 'nothing marked'

    def count(self) -> int:
        return len(self.body_data.lines)

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = wrap_rich(caps, self.body_data.prompt, caps.cols - 6, '  ',
                         p.muted, p.accent)
        rows.append(Text())
        return rows

    def rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        out: list[Text] = []
        for i, ln in enumerate(self.body_data.lines):
            sel = i == self.cursor
            t = selector(caps, sel)
            on = ln.id in self.marked
            t.add('[', p.dim)
            t.add(caps.g('check') if on else ' ', p.accent2 if on else p.dim)
            t.add('] ', p.dim)
            # Output is quoted verbatim and never marked up: a fixture that
            # rendered backticks as styling would be lying about what the tool
            # actually printed.
            t.add(ln.text or ' ', p.fg if (sel or on) else p.muted, bold=sel)
            out.append(t)
        return out

    def activate(self, index: int) -> object:
        """Enter is submit, so activation is the toggle."""
        ln = self.body_data.lines[index]
        self.marked.symmetric_difference_update({ln.id})
        return STAY

    def extra_hints(self) -> list[tuple[str, str]]:
        return [('spc', 'mark'), ('ret', 'submit')]

    def handle(self, key):
        if key.name == 'RET' and not key.ctrl:
            return self._submit()
        if key.name == 'SPC':
            return self.activate(self.cursor)
        return super().handle(key)

    def _submit(self):
        self.watch.lap()
        if self.body_data.actions:
            self._handed_off = True
            return replace(ActScreen(self.session, self.scenario,
                                     tuple(sorted(self.marked)), self.watch))
        score = score_marks(self.body_data.leads, self.body_data.decoys,
                            self.marked, elapsed=self.watch.elapsed())
        self.session.record(self.scenario, score, tuple(sorted(self.marked)))
        from .result import ResultScreen
        return replace(ResultScreen(self.session, self.scenario, score))

    def close(self) -> None:
        if not self._handed_off:
            self.watch.pause()


class ActScreen(ListScreen):
    """Beat two: having spotted it, what does it earn?

    A separate screen rather than a second pane, because the answer to "what
    does this mean" should not be visible while you are still deciding what to
    mark. Reading the options first would tell you what to look for.
    """

    def __init__(self, session: Session, scenario: Scenario,
                 marked: tuple[str, ...], watch) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.marked = marked
        #: The marking screen is closed as this one is pushed, so the watch
        #: arrives paused. Restarting is a no-op when it is already running,
        #: which keeps this correct whichever order the stack unwinds in.
        self.watch = watch
        self.watch.start()
        self.body_data: MarkBody = scenario.body

    @property
    def title(self) -> str:
        return self.scenario.title

    status = 'and now what?'

    def count(self) -> int:
        return len(self.body_data.actions)

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        return [line('  You marked '
                     f'{len(self.marked)} line{"" if len(self.marked) == 1 else "s"}. '
                     'What do you do with it?', p.muted), Text()]

    def rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        out: list[Text] = []
        for i, a in enumerate(self.body_data.actions):
            sel = i == self.cursor
            width = caps.cols - 8
            wrapped = wrap_rich(caps, a.text, width, '', p.fg if sel else p.muted,
                                p.accent)
            first = selector(caps, sel)
            if wrapped:
                first.spans.extend(wrapped[0].spans)
            out.append(first)
            for extra in wrapped[1:]:
                cont = Text().add('     ')
                cont.spans.extend(extra.spans)
                out.append(cont)
        return out

    def activate(self, index: int) -> object:
        a = self.body_data.actions[index]
        self.watch.lap()
        score = score_marks(self.body_data.leads, self.body_data.decoys,
                            self.marked, action_ok=a.correct, has_action=True,
                            elapsed=self.watch.elapsed())
        self.session.record(self.scenario, score, self.marked)
        from .result import ResultScreen
        return replace(ResultScreen(self.session, self.scenario, score, chose=a))

    def close(self) -> None:
        self.watch.pause()
