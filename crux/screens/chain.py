"""Chain mode: one engagement carried through all three tracks.

This is the capstone, and the reason the three tracks are one program. A chain
scenario is three stages in engagement order: sift the output to find the
lead, salvage the proof-of-concept that exploits it, conduit from that foothold
to the next subnet. The fiction runs through all three, so the service you spot
in stage one is the one you exploit in stage two and the host you land in stage
two is where you pivot in stage three.

**Each stage is the real engine, not an imitation of it.** The controller
builds an ordinary `MarkScreen`, `SalvageScreen` or `ConduitScreen` with an
`on_done` callback, so the marking, the broken exploit and the live namespace
network all behave exactly as they do in standalone practice. What changes is
only the ending: instead of stopping at its own result screen, a completed
stage tells the chain, which shows a one-screen bridge into the next stage and
carries on.

**A stumble does not end the engagement.** You always reach all three stages,
because a real box teaches you as much about the pivot when the foothold was a
fight as when it was clean, and the final result reports honestly which stages
you actually completed. That is the difference between "you rooted it" and "you
got a foothold and could not move".
"""

from __future__ import annotations

from ..clock import Stopwatch, fmt
from ..model import ChainBody, Scenario, Stage
from ..render import Caps, Text, bar, line, wrap_rich
from ..scoring import RunScore
from ..session import Session
from ..state import Attempt
from . import POP, ScrollScreen, Screen, replace


def _passed(track: str, score) -> bool:
    if track == 'sift':
        return score.total >= 90 and not score.chased and not score.missed
    return bool(getattr(score, 'landed', False))


def _stage_line(track: str, score) -> tuple[float, str, float]:
    """(0..100, one-line summary, elapsed) normalised across the two score
    types the tracks produce."""
    if track == 'sift':
        return score.total, score.summary(), score.elapsed
    return score.total_score, score.summary(), score.elapsed


class Chain:
    """The controller. Holds the run state and builds each screen in turn.

    Not a Screen itself: the stages are Screens and the app stack owns them.
    The chain threads them together through the `on_done` closures it hands
    each stage, and keeps the scores so the final result can show the whole
    engagement.
    """

    def __init__(self, session: Session, scenario: Scenario) -> None:
        self.session = session
        self.scenario = scenario
        self.body: ChainBody = scenario.body
        self.index = 0
        self.scores: list[tuple[str, object]] = []
        self.watch = Stopwatch(session.clock)
        self.watch.start()

    # -- flow --------------------------------------------------------------

    def _sub_scenario(self, stage: Stage) -> Scenario:
        tier = 'graded' if stage.track == 'sift' else 'verified'
        return Scenario(
            id=f'{self.scenario.id}:{stage.track}', track=stage.track,
            title=stage.title or self.scenario.title, tier=tier,
            body=stage.body, needs=stage.needs,
            source=self.scenario.source, waypoint=self.scenario.waypoint)

    def stage_screen(self, i: int) -> Screen:
        stage = self.body.stages[i]
        sub = self._sub_scenario(stage)
        done = lambda score, _i=i: self._stage_done(_i, score)
        if stage.track == 'sift':
            from .mark import MarkScreen
            return MarkScreen(self.session, sub, on_done=done)
        if stage.track == 'salvage':
            from .salvage import SalvageScreen
            return SalvageScreen(self.session, sub, on_done=done)
        from .conduit import ConduitScreen
        return ConduitScreen(self.session, sub, on_done=done)

    def _stage_done(self, i: int, score):
        self.scores.append((self.body.stages[i].track, score))
        nxt = i + 1
        if nxt < len(self.body.stages):
            return replace(BridgeScreen(self, nxt))
        return replace(ChainResultScreen(self, self._record()))

    def _record(self) -> Attempt:
        passed = sum(1 for track, sc in self.scores if _passed(track, sc))
        total = 100.0 * passed / max(1, len(self.body.stages))
        elapsed = self.watch.elapsed()
        attempt = Attempt(
            scenario=self.scenario.id, track='chain',
            when=self.session.clock.wall(), elapsed=elapsed,
            total=round(total, 1), marks=round(total, 1),
            recall=passed / max(1, len(self.body.stages)), precision=1.0,
            tier='verified', seed=0, marked=())
        self.session.state.record(attempt)
        self.session._save()
        return attempt

    @property
    def passed(self) -> int:
        return sum(1 for track, sc in self.scores if _passed(track, sc))


class ChainIntroScreen(Screen):
    """The engagement brief, before the first stage."""

    def __init__(self, session: Session, scenario: Scenario) -> None:
        self.session = session
        self.scenario = scenario
        self.body_data: ChainBody = scenario.body

    @property
    def title(self) -> str:
        return self.scenario.title

    status = 'engagement'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = wrap_rich(caps, self.body_data.brief, caps.cols - 6, '  ',
                         p.fg, p.accent)
        rows.append(Text())
        rows.append(line('  Three stages, in order:', p.muted))
        names = {'sift': 'find the lead', 'salvage': 'land the exploit',
                 'conduit': 'reach the next host'}
        for i, stage in enumerate(self.body_data.stages, 1):
            rows.append(line(f'    {i}. {stage.track}   '
                             f'{names.get(stage.track, "")}', p.info))
        rows.append(Text())
        rows.append(line('  Press enter to begin.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [(caps.g('enter'), 'begin'), ('esc', 'back'), ('q', 'quit'),
                ('?', 'help')]

    def handle(self, key):
        if key.name == 'RET':
            chain = Chain(self.session, self.scenario)
            return replace(chain.stage_screen(0))
        return super().handle(key)


class BridgeScreen(Screen):
    """The narrative step between two stages.

    One screen, not a full debrief: a full debrief belongs to standalone
    practice, and on a real box nobody stops to explain between the foothold
    and the pivot. What this carries is the story thread and the state you now
    hold, so the next stage starts from somewhere.
    """

    def __init__(self, chain: Chain, index: int) -> None:
        self.chain = chain
        self.index = index
        self.stage: Stage = chain.body.stages[index]

    @property
    def title(self) -> str:
        return self.chain.scenario.title

    @property
    def status(self) -> str:
        return f'stage {self.index + 1} of {len(self.chain.body.stages)}'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        prev_track, prev_score = self.chain.scores[-1]
        good = _passed(prev_track, prev_score)
        head = Text().add('  ')
        head.add(caps.g('check') if good else caps.g('cross'),
                 p.ok if good else p.warn)
        _, summary, _ = _stage_line(prev_track, prev_score)
        head.add(f' {prev_track}: {summary}', p.muted)
        rows = [head, Text()]
        rows.extend(wrap_rich(caps, self.stage.bridge, caps.cols - 6, '  ',
                              p.fg, p.accent))
        rows.append(Text())
        rows.append(line(f'  Next: {self.stage.track}. Press enter.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [(caps.g('enter'), 'continue'), ('H', 'home'), ('q', 'quit'),
                ('?', 'help')]

    def handle(self, key):
        if key.name == 'RET':
            return replace(self.chain.stage_screen(self.index))
        return super().handle(key)


class ChainResultScreen(ScrollScreen):
    """The engagement debrief: every stage, the total, and the through-line."""

    def __init__(self, chain: Chain, attempt: Attempt) -> None:
        super().__init__()
        self.chain = chain
        self.attempt = attempt
        self.body_data: ChainBody = chain.scenario.body

    @property
    def title(self) -> str:
        return self.chain.scenario.title

    @property
    def status(self) -> str:
        n = len(self.body_data.stages)
        return f'{self.chain.passed}/{n} stages'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        passed = self.chain.passed
        n = len(self.body_data.stages)
        rows: list[Text] = []

        head = Text().add('  ')
        head.spans.extend(bar(caps, passed / n, 18).spans)
        clean = passed == n
        head.add('  rooted' if clean else f'  {passed} of {n}',
                 p.ok if clean else p.warn, bold=True)
        head.add(f'   {fmt(self.chain.watch.elapsed())}', p.dim)
        rows.append(head)
        rows.append(Text())

        for track, score in self.chain.scores:
            good = _passed(track, score)
            _, summary, elapsed = _stage_line(track, score)
            row = Text().add('  ')
            row.add(caps.g('check') if good else caps.g('cross'),
                    p.ok if good else p.err)
            row.add(f' {track:<9}', p.fg, bold=True)
            row.add(summary, p.muted)
            row.add(f'   {fmt(elapsed)}', p.dim)
            rows.append(row)

        if self.body_data.debrief:
            rows.append(Text())
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))
        if self.chain.session.save_error:
            rows.append(line(f'  history not saved: '
                             f'{self.chain.session.save_error}', p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
