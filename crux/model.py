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

from .config import SECTIONS, TIERS, TRACKS

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


def roles(lines: tuple[Line, ...]) -> tuple[frozenset[str], frozenset[str]]:
    """(leads, decoys) for one materialised screen.

    A free function rather than a property because from Phase 1 the lines are
    built per attempt from a seed (crux D10), so there is no single set of
    lines a body could answer for.
    """
    return (frozenset(l.id for l in lines if l.kind == 'lead'),
            frozenset(l.id for l in lines if l.kind == 'decoy'))


@dataclass(frozen=True, slots=True)
class MarkBody:
    """A sift scenario: a screen of output, and what in it mattered.

    `fixture` builds the screen from a seed rather than storing it, so the
    noise, the addresses and the lead's position all move between attempts
    (crux D10). What does not move is which entries are leads: those are
    authored, and they keep their ids across every seed.

    `actions` may be empty, which makes the scenario a spot-only drill. A
    scenario whose fixture yields no `lead` lines at all is the crux D9 case
    and is correct by construction: the right answer is to submit having marked
    nothing.
    """

    prompt: str
    fixture: object
    actions: tuple[Action, ...] = ()
    debrief: str = ''

    def build(self, seed: int) -> tuple[Line, ...]:
        return self.fixture.build(seed)

    def canonical(self) -> tuple[Line, ...]:
        """The seed-0 screen. For authoring, `validate.py` and tests only."""
        return self.fixture.canonical()

    @property
    def no_lead(self) -> bool:
        return not roles(self.canonical())[0]


@dataclass(frozen=True, slots=True)
class SalvageBody:
    """A salvage scenario: a broken proof-of-concept and a target to aim it at.

    `broken` is the source the student is handed. `solution` is a reference
    fix that must make the target record a hit, and `validate.py` runs both:
    the solution has to land and the broken one has to fail. That pair of
    checks is what proves the exercise is solvable *and* actually broken,
    which is the defect class that would otherwise ship silently.

    `{{URL}}` and `{{PORT}}` are substituted when the file is written, because
    the target takes an ephemeral port. A scenario whose defect **is** the
    address simply does not use the markers, and then nothing reaching the
    target at all is the correct and most instructive failure.
    """

    brief: str
    filename: str
    broken: str
    solution: str
    requirements: tuple
    defects: tuple[str, ...] = ()
    #: The real CVE and product this exercise is modelled on, shown in-app so
    #: it reads as grounded rather than invented. The target itself stays a
    #: synthetic loopback stand-in (crux D7): the exploit and the defect are
    #: the real ones, the vulnerable service is not.
    cve: str = ''
    models: str = ''
    #: One sentence on how this defect actually broke the real public PoC for
    #: `cve`. Shown after the debrief, so the exercise closes on the real
    #: engagement it is drawn from rather than the synthetic one it ran against.
    real_note: str = ''
    kind: str = 'http'                  # http | tcp
    route: str = '/'
    banner: bytes = b''
    reject_code: int = 400
    reject_message: str = 'Bad request'
    framing: str = 'line'               # tcp only: line | length
    #: A second loopback service the script must never talk to. When this is
    #: set the scenario is a trap: the proof-of-concept quietly contacts it,
    #: and landing requires both that the exploit works **and** that nothing
    #: ever reached here. `{{SINK}}` is substituted with its address.
    trap: tuple = ()
    trap_note: str = ''
    #: Modules the scenario needs to be *absent* for its defect to bite.
    #: `validate.py` asserts they really are, so a machine where one gets
    #: installed reports the problem instead of silently passing.
    needs_absent: tuple[str, ...] = ()
    debrief: str = ''

    def render(self, source: str, url: str, port: int, sink: str = '') -> str:
        return (source.replace('{{URL}}', url)
                      .replace('{{PORT}}', str(port))
                      .replace('{{SINK}}', sink))


@dataclass(frozen=True, slots=True)
class ConduitBody:
    """A conduit scenario: a network you cannot reach across, and a script.

    `starter` is the shell script the student is handed, `solution` is the
    reference tunnel, and `validate.py` runs both: the solution must open the
    path and the starter must not. Same contract as salvage, for the same
    reason.

    `{{ASSETS}}` is substituted with the directory holding the SSH key and
    config, because the key is generated per install and no scenario can know
    its path.
    """

    brief: str
    filename: str
    starter: str
    solution: str
    topology: object
    settle: float = 2.0
    debrief: str = ''

    def render(self, source: str, assets: str) -> str:
        return source.replace('{{ASSETS}}', assets)


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
        if self.track not in SECTIONS:
            raise ContentError(f'{self.id}: unknown track {self.track!r}')
        if self.tier not in TIERS:
            raise ContentError(f'{self.id}: unknown tier {self.tier!r}')
        if not self.id or ' ' in self.id:
            raise ContentError(f'bad scenario id {self.id!r}')


def missing_needs(scenario: Scenario) -> tuple[str, ...]:
    """Binaries a scenario names in `needs` that are not on PATH.

    A scenario with an unmet need is not broken and not a failure: it is a
    tool you have not installed. The UI greys it and says which binary is
    missing, the same way hone handles a module whose real tool is absent.
    `sshd` is special-cased to the two places it hides off a normal PATH.
    """
    import shutil
    out = []
    for tool in scenario.needs:
        if shutil.which(tool):
            continue
        if tool == 'sshd' and any(__import__('os').path.exists(c)
                                  for c in ('/usr/sbin/sshd', '/usr/bin/sshd')):
            continue
        out.append(tool)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Stage:
    """One leg of a chain: a track, a body its engine understands, and the
    narrative that leads into it.

    `title` and `tier` are what the sub-scenario the play-screen sees will
    carry, so a chain stage is scored and rendered exactly as the standalone
    version would be. `needs` rides along for a conduit leg.
    """

    track: str
    body: object
    bridge: str                       # shown before this stage begins
    title: str = ''
    needs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChainBody:
    """A full engagement: find the lead, land the exploit, reach the next host.

    The stages are the three tracks in engagement order, and the fiction runs
    through all of them: the service you spot in stage one is the one you
    exploit in stage two, and the foothold from stage two is where you pivot
    in stage three. That continuity is the whole reason chain mode exists and
    the three tracks are one program rather than three.
    """

    brief: str
    stages: tuple[Stage, ...]
    debrief: str = ''


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
