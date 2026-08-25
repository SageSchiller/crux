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
    #: Set by `app.run` so screens that hand the terminal back for an editor
    #: or a subprocess can do so. None outside a TTY, and the handover helper
    #: degrades to running in place, which is what makes salvage testable.
    terminal: object | None = None
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

    def record_run(self, scenario: Scenario, score) -> Attempt:
        """Record a salvage attempt. Separate from `record` because the two
        tracks measure different things and folding them into one signature
        with six optional arguments would hide that."""
        attempt = Attempt(
            scenario=scenario.id, track=scenario.track,
            when=self.clock.wall(), elapsed=score.elapsed,
            total=score.total_score, marks=score.total_score,
            recall=1.0 if score.landed else 0.0,
            precision=(score.met / score.total) if score.total else 0.0,
            tier=scenario.tier, seed=0, marked=(),
            runs=score.runs, read_first=score.read_first,
        )
        self.state.record(attempt)
        self._save()
        return attempt

    def record_walk(self, scenario: Scenario, score, route=(),
                    seed: int = 0) -> Attempt:
        """Record a lineage attempt.

        `precision` is the share of what you spent that you had to spend, which
        is the same quantity the word means everywhere else in this app: how
        much of what you did was necessary. `marked` holds the route, for the
        reason state.py gives for holding the marks: the score is a number
        nobody can argue with afterwards and the route is the evidence.
        """
        attempt = Attempt(
            scenario=scenario.id, track=scenario.track,
            when=self.clock.wall(), elapsed=score.elapsed,
            total=score.total, marks=score.total,
            recall=1.0 if score.reached else 0.0,
            precision=(min(1.0, score.optimal / score.spent)
                       if score.spent else 0.0),
            tier=scenario.tier, seed=seed, marked=tuple(route))
        self.state.record(attempt)
        self._save()
        return attempt

    def _save(self) -> None:
        if self.read_only:
            return
        try:
            self.state.save()
        except OSError as e:
            self.save_error = str(e)

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
        self._save()
        return attempt
