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
from ..model import MarkBody, Scenario, roles
from ..render import Caps, Text, line, wrap_rich
from ..scoring import score_marks
from ..session import Session
from . import ListScreen, STAY, push, replace, selector


class MarkScreen(ListScreen):
    """A screen of output, and a cursor that marks what mattered."""

    def __init__(self, session: Session, scenario: Scenario,
                 seed: int | None = None, on_done=None) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        #: Set in chain mode. When present the screen advances the chain
        #: instead of recording an attempt and showing its own result, so a
        #: sift stage inside an engagement is scored exactly as the standalone
        #: version but flows on rather than stopping.
        self.on_done = on_done
        self.body_data: MarkBody = scenario.body
        #: A fresh screen per attempt (crux D10). Drawn from the injected clock
        #: rather than from `random`, so a FakeClock makes tests exact and
        #: nothing in library code reads the wall clock behind D17's back.
        if seed is None:
            seed = session.seed_override
        self.seed = (seed if seed is not None
                     else int(session.clock.wall() * 1000) & 0xFFFFFFFF)
        self.lines = self.body_data.build(self.seed)
        self.leads, self.decoys = roles(self.lines)
        self.marked: set[str] = set()
        #: Real tool output is wider than a terminal. A DC's LDAP line runs
        #: past 120 columns and the domain name, which is the whole tell,
        #: lives at the end of it. Truncating would make the scenario
        #: unsolvable at 80 columns, and authoring shorter fake output would
        #: train people to read something nmap does not print. So the screen
        #: pans instead, and the content stays honest.
        self.hscroll = 0
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
        base = f'{n} marked' if n else 'nothing marked'
        return f'{base}   +{self.hscroll}' if self.hscroll else base

    def count(self) -> int:
        return len(self.lines)

    def _text_budget(self, caps: Caps) -> int:
        """Columns left for line text after the frame, cursor and checkbox.

        The trailing 1 is the clip indicator's own column. Without it the row
        came out one wider than the frame, `box_row` truncated it, and the
        indicator was replaced by the generic ellipsis it was meant to
        replace: the screen said "there is more" in the vaguest available way
        while a `pan` hint sat in the footer.
        """
        return max(8, caps.cols - 2 - 3 - 4 - 1)

    def _overflow(self, caps: Caps) -> int:
        """How far the longest line runs past the visible width."""
        longest = max((len(l.text) for l in self.lines), default=0)
        return max(0, longest - self._text_budget(caps))

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = wrap_rich(caps, self.body_data.prompt, caps.cols - 6, '  ',
                         p.muted, p.accent)
        rows.append(Text())
        return rows

    def rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        out: list[Text] = []
        budget = self._text_budget(caps)
        for i, ln in enumerate(self.lines):
            sel = i == self.cursor
            t = selector(caps, sel)
            on = ln.id in self.marked
            t.add('[', p.dim)
            t.add(caps.g('check') if on else ' ', p.accent2 if on else p.dim)
            t.add('] ', p.dim)
            # Output is quoted verbatim and never marked up: a fixture that
            # rendered backticks as styling would be lying about what the tool
            # actually printed.
            shown = ln.text[self.hscroll:]
            clipped = len(shown) > budget
            t.add(shown[:budget] or ' ', p.fg if (sel or on) else p.muted,
                  bold=sel)
            if clipped:
                t.pad_to(budget + 7)
                t.add(caps.g('right'), p.dim)
            out.append(t)
        return out

    def activate(self, index: int) -> object:
        """Enter is submit, so activation is the toggle."""
        ln = self.lines[index]
        self.marked.symmetric_difference_update({ln.id})
        return STAY

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        """Written out rather than extending the base list.

        The base advertises Enter as `select`, which is what it does on every
        other list in the app and is wrong here: on this screen Enter submits
        the whole answer. Inheriting it produced a footer with `ret` in it
        twice, saying two different things.

        `pan` appears only when a line is actually clipped, because a hint for
        a key that does nothing is the rule-4 failure the footer contract
        exists to prevent.
        """
        out = [(caps.g('up') + caps.g('down'), 'move')]
        if self._overflow(caps):
            out.append((caps.g('left') + caps.g('right'), 'pan'))
        out += [('spc', 'mark'), (caps.g('enter'), 'submit'),
                ('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')]
        return out

    def handle(self, key):
        if key.name == 'RET' and not key.ctrl:
            return self._submit()
        if key.name == 'SPC':
            return self.activate(self.cursor)
        # Arrows only. `l` is the base class's activate and `H` is home, so
        # binding the vi pair here would shadow two keys the footer promises.
        if key.name == 'Right':
            self.hscroll += 8
            return STAY
        if key.name == 'Left':
            self.hscroll = max(0, self.hscroll - 8)
            return STAY
        return super().handle(key)

    def body(self, caps: Caps) -> list[Text]:
        # Clamp here rather than in `handle`, because the pan limit depends on
        # the terminal width and a resize must not strand the view past it.
        self.hscroll = max(0, min(self.hscroll, self._overflow(caps)))
        return super().body(caps)

    def _submit(self):
        self.watch.lap()
        if self.body_data.actions:
            self._handed_off = True
            return replace(ActScreen(self.session, self.scenario,
                                     tuple(sorted(self.marked)), self.watch,
                                     self.lines, self.seed, self.on_done))
        score = score_marks(self.leads, self.decoys, self.marked,
                            elapsed=self.watch.elapsed())
        if self.on_done is not None:
            return self.on_done(score)
        self.session.record(self.scenario, score, tuple(sorted(self.marked)),
                            self.seed)
        from .result import ResultScreen
        return replace(ResultScreen(self.session, self.scenario, score,
                                    self.lines))

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
                 marked: tuple[str, ...], watch, lines, seed: int,
                 on_done=None) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.on_done = on_done
        self.marked = marked
        self.lines = lines
        self.seed = seed
        self.leads, self.decoys = roles(lines)
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
        score = score_marks(self.leads, self.decoys, self.marked,
                            action_ok=a.correct, has_action=True,
                            elapsed=self.watch.elapsed())
        if self.on_done is not None:
            return self.on_done(score)
        self.session.record(self.scenario, score, self.marked, self.seed)
        from .result import ResultScreen
        return replace(ResultScreen(self.session, self.scenario, score,
                                    self.lines, chose=a))

    def close(self) -> None:
        self.watch.pause()
