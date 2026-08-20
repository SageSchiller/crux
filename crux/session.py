"""The one mutable thing the screens share.

Screens are otherwise pure: they take `Caps`, return `Text`, and decide what to
push. Recording an attempt is the single exception, because it has to reach
disk, and threading a state object plus a clock plus a registry through every
constructor is how that becomes six constructors deep by Phase 3.

**Saving happens on every recorded attempt, not at exit.** A trainer that loses
an hour of history because the terminal was closed rather than quit is a
trainer people stop trusting, and the file is small enough that the write cost
is irrelevant.
"""

from __future__ import annotations

from dataclasses import dataclass

from .clock import Clock, RealClock
from .loader import Registry, load
from .model import Scenario
from .scoring import Score
from .state import Attempt, State


@dataclass
class Session:
    registry: Registry
    state: State
    clock: Clock
    #: Set when a save failed, so the UI can say so instead of pretending.
    save_error: str = ''
    read_only: bool = False

    @classmethod
    def open(cls, clock: Clock | None = None, read_only: bool = False) -> Session:
        return cls(registry=load(), state=State.load(),
                   clock=clock or RealClock(), read_only=read_only)

    def record(self, scenario: Scenario, score: Score,
               marked: tuple[str, ...] = ()) -> Attempt:
        attempt = Attempt(
            scenario=scenario.id,
            track=scenario.track,
            when=self.clock.wall(),
            elapsed=score.elapsed,
            total=score.total,
            marks=score.marks,
            recall=score.recall,
            precision=score.precision,
            tier=scenario.tier,
            seed=scenario.seed,
            marked=tuple(marked),
            action_ok=score.action_ok,
        )
        self.state.record(attempt)
        if not self.read_only:
            try:
                self.state.save()
            except OSError as e:
                self.save_error = str(e)
        return attempt
