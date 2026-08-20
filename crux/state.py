"""On-disk state: attempt history and nothing else (crux D16).

A JSON file at `$XDG_DATA_HOME/crux/state.json`, with explicit export and
import for moving between machines.

**What is stored and why it is only this.** One row per attempt: which
scenario, when, what was marked, what it scored, and how long it took. There is
no derived state, no cached progress, no "current position" that could
disagree with the history it was derived from. Everything the app shows about
your progress is computed from the rows at read time, which means the file
cannot develop an internal contradiction and there is no migration to write
when the display changes.

**Elapsed time is a first-class column from the first commit (crux D12)**, not
because anything reads it yet but because `proctor` cannot be built on history
that does not have it and it can never be backfilled.

**Marked ids are stored, not just the score.** A score is a number you cannot
argue with after the fact; the marks are the evidence. If a scenario's key
turns out to be wrong, the stored marks are what lets an old attempt be
rescored rather than discarded, and given that content accuracy is the thing
Waypoint's box walk spent six passes on, assume some keys will be wrong.

**Reads never raise.** A corrupt or unreadable state file loses history, which
is bad, but refusing to start loses the app, which is worse. Corruption is
reported once on the home screen rather than thrown.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import state_path

VERSION = 1


@dataclass(frozen=True, slots=True)
class Attempt:
    scenario: str
    track: str
    when: float          # wall-clock unix seconds, for display order only
    elapsed: float       # monotonic seconds on task (crux D12)
    total: float
    marks: float
    recall: float
    precision: float
    tier: str
    seed: int = 0
    marked: tuple[str, ...] = ()
    action_ok: bool | None = None
    #: salvage only. Recorded, never scored: `proctor` needs the pacing and
    #: the crux D19 capstone needs to know whether the file was ever opened
    #: before it was executed. Neither can be backfilled.
    runs: int = 0
    read_first: bool | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Attempt:
        return cls(
            scenario=str(d.get('scenario', '')),
            track=str(d.get('track', '')),
            when=float(d.get('when', 0.0)),
            elapsed=float(d.get('elapsed', 0.0)),
            total=float(d.get('total', 0.0)),
            marks=float(d.get('marks', 0.0)),
            recall=float(d.get('recall', 0.0)),
            precision=float(d.get('precision', 0.0)),
            tier=str(d.get('tier', 'self')),
            seed=int(d.get('seed', 0)),
            marked=tuple(d.get('marked') or ()),
            action_ok=d.get('action_ok'),
            runs=int(d.get('runs', 0)),
            read_first=d.get('read_first'),
        )


@dataclass
class State:
    attempts: list[Attempt] = field(default_factory=list)
    #: Set when the file on disk could not be read. Shown once, never thrown.
    damaged: str = ''

    # -- history -----------------------------------------------------------

    def record(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)

    def for_scenario(self, scenario_id: str) -> list[Attempt]:
        return [a for a in self.attempts if a.scenario == scenario_id]

    def best(self, scenario_id: str) -> Attempt | None:
        rows = self.for_scenario(scenario_id)
        return max(rows, key=lambda a: a.total) if rows else None

    def attempted(self, scenario_id: str) -> bool:
        return any(a.scenario == scenario_id for a in self.attempts)

    def track_summary(self, track: str) -> tuple[int, float]:
        """(scenarios attempted, mean best score) for one track."""
        best: dict[str, float] = {}
        for a in self.attempts:
            if a.track == track:
                best[a.scenario] = max(best.get(a.scenario, 0.0), a.total)
        if not best:
            return 0, 0.0
        return len(best), sum(best.values()) / len(best)

    def time_on_task(self, track: str | None = None) -> float:
        return sum(a.elapsed for a in self.attempts
                   if track is None or a.track == track)

    # -- persistence -------------------------------------------------------

    def to_dict(self) -> dict:
        return {'version': VERSION,
                'attempts': [asdict(a) for a in self.attempts]}

    @classmethod
    def from_dict(cls, d: dict) -> State:
        rows = d.get('attempts') or []
        return cls(attempts=[Attempt.from_dict(r) for r in rows
                             if isinstance(r, dict)])

    @classmethod
    def load(cls, path: Path | None = None) -> State:
        p = path or state_path()
        try:
            raw = p.read_text(encoding='utf-8')
        except FileNotFoundError:
            return cls()
        except OSError as e:
            return cls(damaged=f'could not read {p}: {e}')
        try:
            return cls.from_dict(json.loads(raw))
        except (ValueError, TypeError) as e:
            return cls(damaged=f'{p} is not readable JSON: {e}')

    def save(self, path: Path | None = None) -> None:
        """Write atomically. A half-written state file is worse than none."""
        p = path or state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix='.state-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(self.to_dict(), fh, indent=1, sort_keys=True)
            os.replace(tmp, p)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- export and import -------------------------------------------------

    def export_json(self) -> str:
        return json.dumps(self.to_dict(), indent=1, sort_keys=True)

    def merge(self, other: State) -> int:
        """Union by (scenario, when, elapsed). Returns rows added.

        Merge rather than replace, because importing on a machine that already
        has history should not silently delete it. Duplicate detection is on
        the triple rather than on equality so that an identical rescored row
        does not import twice.
        """
        seen = {(a.scenario, round(a.when, 3), round(a.elapsed, 3))
                for a in self.attempts}
        added = 0
        for a in other.attempts:
            k = (a.scenario, round(a.when, 3), round(a.elapsed, 3))
            if k not in seen:
                seen.add(k)
                self.attempts.append(a)
                added += 1
        self.attempts.sort(key=lambda a: a.when)
        return added
