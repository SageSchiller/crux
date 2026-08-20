"""The scenario schema (crux D18) and the per-track bodies.

One `Scenario` type across all three tracks, with a track-specific `body`. The
shared fields are the ones the harness needs (id, track, tier, order) and the
ones auditing needs (`source`, `waypoint`, `seed`). The body is whatever the
track's engine understands, and the harness never looks inside it.

**Why `source` and `waypoint` are on the base type and not optional extras
(crux D11).** Waypoint's box walk cost 107 defects and six passes to learn that
content without traceable provenance cannot be audited, only re-read. Every
scenario here names the writeup it came from and, where one applies, the
Waypoint node that teaches the thing you missed. The 191 PEN-200 writeups
already reference 174 distinct node ids, so populating this is transcription
rather than invention.

**Why a sift line carries its own role rather than the scenario carrying a set
of correct line numbers.** A key held separately can reference a line that the
fixture builder no longer produces, and the failure mode is a scenario that is
silently unsolvable. Roles attached to lines cannot drift from the lines they
describe, so that whole defect class is unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import TIERS, TRACKS

#: What a line in a sift fixture is *for*. `lead` is the thing that mattered,
#: `decoy` is authored to tempt (and costs more when chased, per crux D8), and
#: `noise` is everything a real screen is mostly made of.
LINE_KINDS = ('lead', 'decoy', 'noise')


class ContentError(ValueError):
    """Raised when authored content is malformed. A content bug, not a user bug."""


@dataclass(frozen=True, slots=True)
class Line:
    """One line of a sift fixture."""

    id: str
    text: str
    kind: str = 'noise'

    def __post_init__(self) -> None:
        if self.kind not in LINE_KINDS:
            raise ContentError(f'line {self.id!r}: bad kind {self.kind!r}')


@dataclass(frozen=True, slots=True)
class Action:
    """One option in the `act` beat: having spotted it, what does it earn?

    `why` is shown either way. A wrong option that explains why it is wrong is
    worth more than a right one that explains nothing, because the wrong ones
    are where the reasoning actually lives: right idea wrong order, right tool
    wrong target, and the classic rabbit hole.
    """

    text: str
    correct: bool = False
    why: str = ''


@dataclass(frozen=True, slots=True)
class MarkBody:
    """A sift scenario: a screen of output, and what in it mattered.

    `actions` may be empty, which makes the scenario a spot-only drill. A
    scenario with no `lead` lines at all is the crux D9 case and is correct by
    construction: the right answer is to submit having marked nothing.
    """

    prompt: str
    lines: tuple[Line, ...]
    actions: tuple[Action, ...] = ()
    debrief: str = ''

    @property
    def leads(self) -> frozenset[str]:
        return frozenset(l.id for l in self.lines if l.kind == 'lead')

    @property
    def decoys(self) -> frozenset[str]:
        return frozenset(l.id for l in self.lines if l.kind == 'decoy')

    @property
    def no_lead(self) -> bool:
        return not self.leads


@dataclass(frozen=True, slots=True)
class StubBody:
    """A track whose engine is not built yet.

    Exists so the harness can be proven end to end before `salvage` and
    `conduit` have engines, and it is `self` tier and says so on screen rather
    than pretending to check anything. That is crux D6 and D14 applied to the
    app's own incompleteness: if the honesty rule does not bind when it is
    merely inconvenient, it does not bind.
    """

    prompt: str
    phase: str
    debrief: str = ''


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    track: str
    title: str
    tier: str
    order: int = 0
    body: object = None
    #: Provenance (crux D11). Vault-relative path of the writeup it came from.
    source: str = ''
    #: The Waypoint node that teaches this, where one applies (crux D11).
    waypoint: str = ''
    #: hone modules this leans on, for the "you could not drive the tool" case.
    hone: tuple[str, ...] = ()
    #: Binaries required, absent which the scenario is skipped, not failed.
    needs: tuple[str, ...] = ()
    #: Fixture seed (crux D10), so a run is reproducible and tests deterministic.
    seed: int = 0

    def __post_init__(self) -> None:
        if self.track not in TRACKS:
            raise ContentError(f'{self.id}: unknown track {self.track!r}')
        if self.tier not in TIERS:
            raise ContentError(f'{self.id}: unknown tier {self.tier!r}')
        if not self.id or ' ' in self.id:
            raise ContentError(f'bad scenario id {self.id!r}')


@dataclass
class Track:
    """A track and the scenarios loaded into it."""

    name: str
    blurb: str
    scenarios: list[Scenario] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """False while every scenario in the track is still a stub."""
        return any(not isinstance(s.body, StubBody) for s in self.scenarios)
