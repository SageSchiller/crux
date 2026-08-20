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
    #: `--seed N` pins every fixture instead of drawing one per attempt.
    #: Exists for two real jobs: reproducing an attempt from its stored seed
    #: when a key turns out to be wrong, and letting `test-tty.py` know where
    #: the lead is. Off by default, because a pinned seed defeats crux D10.
    seed_override: int | None = None

    @classmethod
    def open(cls, clock: Clock | None = None, read_only: bool = False,
             seed_override: int | None = None) -> Session:
        return cls(registry=load(), state=State.load(),
                   clock=clock or RealClock(), read_only=read_only,
                   seed_override=seed_override)

    def record(self, scenario: Scenario, score: Score,
               marked: tuple[str, ...] = (), seed: int | None = None) -> Attempt:
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
            seed=scenario.seed if seed is None else seed,
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
