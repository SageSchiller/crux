"""The arithmetic behind `proctor`: where the clock went, and what it bought.

Everything here is a pure function of recorded attempts and authored numbers.
Nothing reads a clock (crux D17), nothing touches disk, and nothing renders:
the screens in `screens/proctor.py` ask this module questions and draw the
answers. That separation is what makes a pacing verdict testable, and a pacing
verdict that cannot be tested is an opinion.

**The three numbers this module exists to produce.**

*Allocation* is a leg's share of the sitting's budget. It is not a par time and
it is not a claim about how long the exercise takes; it is how much of your
clock that leg is entitled to if you spread the budget evenly across the work.
The moment you cross it you are spending someone else's time.

*Overrun* is how far past the allocation a leg ran. On its own it is not a
fault: a leg that overruns and lands has bought the time it took.

*Sunk* is overrun on a leg that scored **zero**, and it is the number the whole
track is built to show you. It is the time you spent past your own allocation
on something that paid nothing at all: the four hours on the box that was never
going to fall, expressed in the only units an exam actually counts. Nobody has
ever been shown this number about themselves, which is exactly why it is the
headline.

**Why sunk is defined on a zero score rather than on a low one.** A leg that
overran and came away with forty points bought something, and pricing that
would mean deciding what a partial result is worth per minute, which is a
judgement crux has no basis to make. Zero is unambiguous: the clock ran and
nothing came back. Abandoning early is handled by the same definition without a
special case, because a leg you walked away from inside its allocation has no
overrun and therefore nothing sunk. That is the correct answer and it falls out
of the arithmetic rather than being written into it.

**On `TRACK_WEIGHT`, and the difference between this and `DECOY_WEIGHT`.**
`DECOY_WEIGHT` stopped being a guess because it could be profiled over the
content set with nobody playing: the scorer's behaviour is a property of the
authored screens. Track weight is not like that. It is a claim about how long a
human takes, and the only evidence that could settle it is human play, of which
there is currently almost none in this history. So the numbers below are
**stated as an estimate and labelled as one**, `validate.py --pacing` prints
them beside whatever the real history says, and they should not move until
there are enough attempts per track to be worth reading. Pretending otherwise
would be the same failure `--scores` was built to prevent, one level up.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .clock import fmt
from .config import TRACKS

#: A leg's share of the budget, relative to the other legs. An **estimate**,
#: not a measurement: sift is a read and a decision, lineage is a longer read
#: and several decisions, salvage and conduit are edit-run loops that also pay
#: for a build and a probe on every attempt. See
#: the module docstring for why this one is allowed to be an estimate when
#: `DECOY_WEIGHT` was not, and `validate.py --pacing` for the tuning path.
TRACK_WEIGHT = {'sift': 1.0, 'salvage': 3.0, 'conduit': 3.0,
                'lineage': 2.0}

#: Attempts per track before the measured median is worth reading against the
#: weight above. Below this, `--pacing` prints the sample size and declines to
#: draw a conclusion, which is the honest thing for a number this small.
SAMPLE_FLOOR = 8


def weight(track: str) -> float:
    return TRACK_WEIGHT.get(track, 1.0)


def allocations(tracks, budget: float) -> tuple[float, ...]:
    """Each leg's share of `budget`, in seconds, weighted by its track.

    Takes the track names rather than the slots so the fixture-free arithmetic
    can be tested on its own, and so a caller that has already resolved slots
    to scenarios does not have to hold on to the slots as well.
    """
    ws = [weight(t) for t in tracks]
    total = sum(ws)
    if total <= 0:
        return tuple(0.0 for _ in ws)
    return tuple(budget * w / total for w in ws)


# --------------------------------------------------------------------------
# One sitting
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Leg:
    """One slot of a sitting, after it was played, abandoned or never reached."""

    scenario: str
    track: str
    title: str
    allocation: float
    elapsed: float = 0.0
    score: float = 0.0
    reached: bool = False
    abandoned: bool = False

    @property
    def overrun(self) -> float:
        if not self.reached:
            return 0.0
        return max(0.0, self.elapsed - self.allocation)

    @property
    def paid(self) -> bool:
        return self.score > 0.0

    @property
    def sunk(self) -> float:
        """Overrun on a leg that scored nothing. The number that matters."""
        return 0.0 if self.paid else self.overrun

    @property
    def verdict(self) -> str:
        """One word for the row, in the order a reader needs them."""
        if not self.reached:
            return 'never reached'
        if self.abandoned:
            return 'walked away'
        if not self.paid:
            return 'nothing for it'
        if self.overrun:
            return 'landed, over'
        return 'landed'


@dataclass(frozen=True, slots=True)
class SittingReview:
    """The post-mortem for one sitting. Every field is shown to the student."""

    legs: tuple[Leg, ...]
    budget: float
    target: float
    #: Wall time the sitting actually consumed, from the first leg opening to
    #: the last one closing. **Not** the sum of the legs: the screens between
    #: them are read on the clock too, and a budget that only charged you for
    #: time inside an exercise would be lying about where the hour went.
    spent: float = 0.0

    # -- score -------------------------------------------------------------

    @property
    def score(self) -> float:
        """Mean over **every** slot, so a leg you never reached costs you.

        Averaging only what you played would score a student who did one leg
        perfectly and ran out of clock at 100, which is the precise opposite
        of what an exam measures.
        """
        if not self.legs:
            return 0.0
        return sum(l.score for l in self.legs) / len(self.legs)

    @property
    def passed(self) -> bool:
        return self.score >= self.target

    # -- clock -------------------------------------------------------------

    @property
    def on_legs(self) -> float:
        """Time inside the exercises. `spent - on_legs` is what the reading
        and the deciding between them cost."""
        return sum(l.elapsed for l in self.legs if l.reached)

    @property
    def banked(self) -> float:
        return max(0.0, self.budget - self.spent)

    @property
    def overspent(self) -> float:
        """Time past the budget. The last leg is allowed to finish, so a
        sitting can end slightly over rather than cutting mid-answer."""
        return max(0.0, self.spent - self.budget)

    @property
    def sunk(self) -> float:
        return sum(l.sunk for l in self.legs)

    @property
    def overrun(self) -> float:
        return sum(l.overrun for l in self.legs)

    # -- populations -------------------------------------------------------

    @property
    def unreached(self) -> tuple[Leg, ...]:
        return tuple(l for l in self.legs if not l.reached)

    @property
    def abandons(self) -> tuple[Leg, ...]:
        return tuple(l for l in self.legs if l.abandoned)

    @property
    def landed(self) -> tuple[Leg, ...]:
        return tuple(l for l in self.legs if l.reached and l.paid)

    @property
    def dry(self) -> tuple[Leg, ...]:
        """Reached, not abandoned, and scored nothing: ridden to the end."""
        return tuple(l for l in self.legs
                     if l.reached and not l.abandoned and not l.paid)

    @property
    def sank(self) -> tuple[Leg, ...]:
        """Legs that actually sank time, which is **not** the same set as
        `dry`: a leg you walked away from late sank whatever it spent past
        its share, and a leg you rode to the end inside its share sank
        nothing. Counting `dry` here produced a note that read '14m 40s went
        past your own allocation on 0 legs', which is the sort of arithmetic
        nobody trusts a tool about twice."""
        return tuple(l for l in self.legs if l.sunk > 0)

    # -- the verdict -------------------------------------------------------

    def headline(self) -> str:
        """One sentence, in the words a person would use about their own run."""
        t = f'{self.target:.0f}'
        if self.passed:
            if self.banked >= 60:
                return (f'Cleared {t} with {fmt(self.banked)} still on the '
                        f'clock. That is the shape you want.')
            return f'Cleared {t}, and used very nearly all of it.'
        if self.unreached and self.sunk:
            return (f'Short of {t}. {fmt(self.sunk)} went into legs that paid '
                    f'nothing, and {len(self.unreached)} you never reached.')
        if self.unreached:
            return (f'Short of {t}, with {len(self.unreached)} leg'
                    f'{"" if len(self.unreached) == 1 else "s"} you never '
                    f'reached.')
        if self.sunk:
            return (f'Short of {t}. {fmt(self.sunk)} of the budget bought '
                    f'nothing at all.')
        return f'Short of {t}. The clock was not the problem here.'

    def notes(self) -> tuple[str, ...]:
        """The teaching, one sentence each, only where there is something to say."""
        out: list[str] = []

        if self.sunk:
            n = len(self.sank)
            out.append(
                f'**{fmt(self.sunk)}** went past your own allocation on '
                f'{n} leg{"" if n == 1 else "s"} that scored zero. On a real '
                f'sitting that is the whole difference between finishing and '
                f'not.')

        if self.abandons:
            for leg in self.abandons:
                if leg.elapsed <= leg.allocation:
                    out.append(
                        f'You walked away from **{leg.title}** at '
                        f'{fmt(leg.elapsed)}, inside its {fmt(leg.allocation)} '
                        f'share. That is the decision this track exists to '
                        f'train, and you made it.')
                else:
                    out.append(
                        f'You walked away from **{leg.title}** at '
                        f'{fmt(leg.elapsed)}, {fmt(leg.overrun)} past its '
                        f'share. The call was right; it came late.')
        elif self.dry:
            out.append(
                'You abandoned nothing. Every leg that was going nowhere was '
                'ridden to the end of it, which is the most expensive habit '
                'on this list.')

        if self.unreached:
            names = ', '.join(l.title for l in self.unreached)
            out.append(f'Never reached: {names}. Those are the points the '
                       f'clock cost you, not the technique.')

        if self.banked >= 60 and not self.passed and not self.unreached:
            out.append(
                f'You finished with {fmt(self.banked)} unspent and still fell '
                f'short, so the budget was not the binding constraint. That '
                f'is a content problem, not a pacing one, and it is the '
                f'better of the two to have.')

        if self.overspent:
            out.append(f'You ran {fmt(self.overspent)} past the budget. The '
                       f'last leg is allowed to finish; on the day it is not.')

        if not out:
            out.append('Nothing to correct: every leg came in on its share.')
        return tuple(out)


def review(legs, budget: float, target: float,
           spent: float | None = None) -> SittingReview:
    legs = tuple(legs)
    if spent is None:
        spent = sum(l.elapsed for l in legs if l.reached)
    return SittingReview(legs=legs, budget=budget, target=target,
                         spent=spent)


# --------------------------------------------------------------------------
# Filling the slots
# --------------------------------------------------------------------------

def family(scenario_id: str) -> str:
    """The middle segment of a scenario id: `sift-nmap-pinned` -> `nmap`.

    Ids are authored `track-family-variant` throughout, so this reads the
    grouping that already exists rather than adding a field for it.
    """
    parts = scenario_id.split('-')
    return parts[1] if len(parts) > 2 else scenario_id


def _sort_key(scenario, state, taken_families):
    """Never played first, then a family this sitting has not used, then
    longest ago, then authored order.

    **Why family diversity is a tie-break and not the first rule.** Unseen
    content is what keeps a sitting an honest test of pacing, so it wins. But
    on a fresh install everything is unseen, every key ties, and authored order
    decides: the first sitting anyone ever sat would have been three screens of
    `nmap` output, which is a worse drill and a worse advertisement for the
    track. Spreading across families costs nothing when the first rule is
    already satisfied and fixes exactly that case.

    Deterministic given a history, which is what lets `test.py` assert a
    sitting's composition instead of asserting that it has the right length.
    """
    when = state.last_when(scenario.id)
    return (1 if when is not None else 0,
            1 if family(scenario.id) in taken_families else 0,
            when or 0.0, scenario.order, scenario.id)


def fill(slots, registry, state) -> tuple[object, ...]:
    """Pick one scenario per slot: unseen first, then least recently played.

    A slot whose pool cannot be filled yields `None` rather than raising, and
    the caller decides what to do about it. `validate.py` is what guarantees
    this does not happen in shipped content; at runtime, a scenario made
    unplayable by a missing tool is a normal condition rather than a bug, and
    a sitting that crashed because `chisel` is not installed would be a worse
    answer than one that quietly picks something else.
    """
    from .model import missing_needs

    chosen: list[object] = []
    taken: set[str] = set()
    families: set[str] = set()
    for slot in slots:
        pool = registry.track(slot.track).scenarios
        if slot.pool:
            allowed = set(slot.pool)
            pool = [s for s in pool if s.id in allowed]
        pool = [s for s in pool if s.id not in taken and not missing_needs(s)]
        if not pool:
            chosen.append(None)
            continue
        pick = min(pool, key=lambda s: _sort_key(s, state, families))
        taken.add(pick.id)
        families.add(family(pick.id))
        chosen.append(pick)
    return tuple(chosen)


# --------------------------------------------------------------------------
# The whole history
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TrackPacing:
    """What one track has cost you, across every attempt ever recorded.

    `median` is taken over **completed** attempts only, while `on_task` and
    the zero figures count everything. The two questions are different and
    folding them together would answer neither: how long a scenario takes is
    a property of the work, and an attempt you walked away from at ninety
    seconds says nothing about that. Where your clock went is a property of
    you, and the ninety seconds were yours.
    """

    track: str
    attempts: int
    completed: int
    scenarios: int
    median: float
    longest: float
    on_task: float
    zeros: int
    zero_time: float

    @property
    def thin(self) -> bool:
        """Too few completed attempts for the median to mean anything."""
        return self.completed < SAMPLE_FLOOR


@dataclass(frozen=True, slots=True)
class HistoryPacing:
    """The standalone post-mortem: every attempt, not just one sitting."""

    tracks: tuple[TrackPacing, ...]
    total_time: float
    zero_time: float
    attempts: int
    sittings: int
    abandons: int
    ran_unread: int
    longest: object | None = None

    @property
    def any(self) -> bool:
        return bool(self.attempts)

    @property
    def zero_share(self) -> float:
        return self.zero_time / self.total_time if self.total_time else 0.0

    def notes(self) -> tuple[str, ...]:
        out: list[str] = []
        if not self.any:
            return ('Nothing recorded yet. Play a few scenarios and this '
                    'becomes a picture of where your clock actually goes.',)

        if self.zero_time:
            out.append(
                f'**{fmt(self.zero_time)}** of your {fmt(self.total_time)} on '
                f'task went into attempts that scored zero, '
                f'{self.zero_share * 100:.0f}% of everything you have spent '
                f'here. Some of that is how learning looks; the question is '
                f'whether any single one of them should have been cut earlier.')

        if self.longest is not None:
            out.append(
                f'Your longest single attempt was {fmt(self.longest.elapsed)} '
                f'on `{self.longest.scenario}`, and it scored '
                f'{self.longest.total:.0f}.')

        if self.ran_unread:
            out.append(
                f'You ran a proof-of-concept without opening it first '
                f'**{self.ran_unread}** time'
                f'{"" if self.ran_unread == 1 else "s"}. That is the '
                f'read-it-before-you-run-it habit, measured rather than '
                f'warned about.')

        thin = [t.track for t in self.tracks if t.thin and t.attempts]
        if thin:
            out.append(
                f'Sample is still thin for {", ".join(thin)} (under '
                f'{SAMPLE_FLOOR} completed attempts), so the medians above '
                f'are a sketch rather than a measurement.')

        if not self.sittings:
            out.append('You have not sat a timed sitting yet. Time on task is '
                       'not pacing until something is competing for it.')
        return tuple(out)


def history(attempts) -> HistoryPacing:
    """Fold every recorded attempt into a pacing picture.

    Sitting summary rows are excluded from the per-track figures: a `proctor`
    row's elapsed time is the whole sitting, so counting it alongside the legs
    it contains would charge the same minutes twice.
    """
    rows = [a for a in attempts if a.track != 'proctor']
    tracks: list[TrackPacing] = []
    for name in TRACKS:
        mine = [a for a in rows if a.track == name]
        if not mine:
            tracks.append(TrackPacing(name, 0, 0, 0, 0.0, 0.0, 0.0, 0, 0.0))
            continue
        times = [a.elapsed for a in mine]
        done = [a.elapsed for a in mine if not a.abandoned]
        zeros = [a for a in mine if a.total <= 0]
        tracks.append(TrackPacing(
            track=name,
            attempts=len(mine),
            completed=len(done),
            scenarios=len({a.scenario for a in mine}),
            median=statistics.median(done) if done else 0.0,
            longest=max(times),
            on_task=sum(times),
            zeros=len(zeros),
            zero_time=sum(a.elapsed for a in zeros),
        ))

    total = sum(a.elapsed for a in rows)
    zero_time = sum(a.elapsed for a in rows if a.total <= 0)
    longest = max(rows, key=lambda a: a.elapsed) if rows else None
    return HistoryPacing(
        tracks=tuple(tracks),
        total_time=total,
        zero_time=zero_time,
        attempts=len(rows),
        sittings=sum(1 for a in attempts if a.track == 'proctor'),
        abandons=sum(1 for a in rows if a.abandoned),
        ran_unread=sum(1 for a in rows if a.read_first is False),
        longest=longest,
    )
