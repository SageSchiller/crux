"""Time, always injected, never read from library code (crux D17).

Two reasons this is a module rather than a call to `time.monotonic()` wherever
it is needed. The first is the ordinary one: a scheduler that reads the wall
clock cannot be tested deterministically.

The second is specific to crux and is the reason D17 is locked rather than
merely preferred. **Elapsed time is a scored quantity here**, not just a
display: D12 records time on task from the first commit so that `proctor`, the
exam-pacing track, has history to analyse when it is built. A number that feeds
a score has to be reproducible in a test, or the score cannot be trusted.

`monotonic` rather than wall time for durations, because a duration that can go
backwards when NTP steps the clock is a duration that can produce a negative
elapsed time in someone's saved history.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class Clock:
    """Interface. Two implementations: the real one and the test one."""

    def monotonic(self) -> float:
        raise NotImplementedError

    def wall(self) -> float:
        """Unix timestamp, for stamping history. Never used for durations."""
        raise NotImplementedError


class RealClock(Clock):
    def monotonic(self) -> float:
        return time.monotonic()

    def wall(self) -> float:
        return time.time()


@dataclass
class FakeClock(Clock):
    """Advance it by hand. Used by `test.py` and by nothing else."""

    t: float = 0.0
    epoch: float = 1_755_000_000.0

    def monotonic(self) -> float:
        return self.t

    def wall(self) -> float:
        return self.epoch + self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@dataclass
class Stopwatch:
    """Time on task for one scenario attempt (crux D12).

    Pausable, because a scenario the student walked away from mid-way would
    otherwise report an elapsed time that says more about lunch than about
    pacing. `salvage` and `conduit` both hand the terminal back so real work
    can happen elsewhere, and that handover is exactly when the watch stops.
    """

    clock: Clock
    started: float = 0.0
    accrued: float = 0.0
    running: bool = False
    _laps: list[float] = field(default_factory=list)

    def start(self) -> None:
        if not self.running:
            self.started = self.clock.monotonic()
            self.running = True

    def pause(self) -> None:
        if self.running:
            self.accrued += self.clock.monotonic() - self.started
            self.running = False

    def elapsed(self) -> float:
        live = (self.clock.monotonic() - self.started) if self.running else 0.0
        return self.accrued + live

    def lap(self) -> float:
        """Mark a beat within one scenario (spot, then act) and return it."""
        e = self.elapsed()
        self._laps.append(e - sum(self._laps))
        return self._laps[-1]

    @property
    def laps(self) -> tuple[float, ...]:
        return tuple(self._laps)


def fmt(seconds: float) -> str:
    """`4m 12s`, or `38s` under a minute. Never a bare float on screen."""
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f'{seconds:.0f}s'
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f'{m}m {s:02d}s'
    h, m = divmod(m, 60)
    return f'{h}h {m:02d}m'
