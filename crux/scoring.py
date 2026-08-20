"""Scoring, and the arithmetic that makes crux D8 true.

**The decision this module implements.** If recall alone were scored, the
winning strategy in `sift` would be to mark every line, which is precisely the
real-world failure being trained: chase everything, run out of clock. So the
score is the harmonic mean of precision and recall, and a decoy costs more than
a blank line, because a decoy is what a rabbit hole actually looks like at the
moment you decide to enter it.

Worked example, on a forty-line screen with two leads and three decoys:

* mark the two leads and nothing else: precision 1.0, recall 1.0, **100**
* mark all forty: recall 1.0, precision 0.05, **9**
* find one lead, chase nothing: precision 1.0, recall 0.5, **67**
* find both leads, chase one decoy: precision 0.5, recall 1.0, **67**

The last two landing on the same number is the point of the whole design:
**on a screen with more than one lead, missing one costs what chasing a decoy
costs**. A scorer that punished only one of them would teach the other.

That symmetry does not hold, and should not, when a screen has exactly one
lead. Missing it means you came away with nothing, so it scores zero while
chasing a decoy alongside a correct find scores 50. Half the content is
single-lead, so this is the common case rather than an edge one, and it is
correct: "found nothing" and "found it and also chased something" are not the
same outcome.

**`DECOY_WEIGHT` is measured, not guessed.** Profiled across all 26 authored
scenarios with `validate.py --scores`: at 2.0 marking everything averages 11
out of 100 and never exceeds 21; at 3.0 the greedy average only moves to 10,
while chasing one decoy on a two-lead screen drops to 57 against 67 for
missing a lead, which inverts the relationship this scorer exists to express.
2.0 stays.

**The no-lead case (crux D9).** Some screens contain nothing. Recall is
vacuously satisfied and the only thing left to measure is restraint, so the
score is driven entirely by what you marked that you should not have. A clean
"nothing here, move on" is worth full marks, and it has to be, or the app
trains the exact instinct that produces rabbit holes.

**Time is recorded, not folded in (crux D12).** Elapsed time rides along on the
result and lands in history, and nothing here reads it. Pacing is `proctor`'s
subject, and a scorer that quietly penalised slowness would be answering a
question this track is not asking.
"""

from __future__ import annotations

from dataclasses import dataclass

#: A decoy is authored to tempt, so chasing one costs double a stray mark.
#: Profiled over the whole content set in Phase 2; see the module docstring
#: for the numbers that kept it at 2.0 rather than 3.0.
DECOY_WEIGHT = 2.0

#: What the `act` beat is worth when a scenario has one. Marking is three
#: quarters of the score because spotting is the harder half and the half that
#: cannot be guessed from a short list.
ACTION_POINTS = 25.0

BANDS = ((90.0, 'clean'), (70.0, 'solid'), (50.0, 'workable'), (25.0, 'thin'))


def band(score: float) -> str:
    for floor, name in BANDS:
        if score >= floor:
            return name
    return 'lost'


@dataclass(frozen=True, slots=True)
class Score:
    """The result of one sift attempt. Every field is shown to the user.

    `chased` is deliberately as prominent as `missed` on the result screen.
    Everyone knows what they failed to find; almost nobody has ever been shown
    a count of what they went after that was never going to pay.
    """

    found: tuple[str, ...]
    missed: tuple[str, ...]
    chased_decoys: tuple[str, ...]
    chased_noise: tuple[str, ...]
    recall: float
    precision: float
    marks: float          # marking beat, 0..100
    action_ok: bool | None
    total: float          # marking plus the act beat, 0..100
    no_lead: bool
    elapsed: float = 0.0

    @property
    def band(self) -> str:
        return band(self.total)

    @property
    def chased(self) -> tuple[str, ...]:
        return self.chased_decoys + self.chased_noise

    @property
    def clean_pass(self) -> bool:
        """Found everything, chased nothing, and got the follow-up right."""
        return (not self.missed and not self.chased
                and self.action_ok is not False)

    def summary(self) -> str:
        """One line, and the one that should sting when it should sting."""
        if self.no_lead:
            if not self.chased:
                return 'nothing here, and you said so'
            return f'nothing here, and you chased {len(self.chased)}'
        got = f'found {len(self.found)} of {len(self.found) + len(self.missed)}'
        if not self.chased:
            return f'{got}, chased nothing'
        return f'{got}, chased {len(self.chased)}'


def _f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_marks(leads, decoys, marked, action_ok: bool | None = None,
                has_action: bool = False, elapsed: float = 0.0) -> Score:
    """Score one sift attempt.

    `leads` and `decoys` are id sets from the scenario body; `marked` is what
    the student actually selected. Anything marked that is neither a lead nor a
    decoy is noise, and costs a single unit.
    """
    leads, decoys, marked = frozenset(leads), frozenset(decoys), frozenset(marked)

    found = tuple(sorted(marked & leads))
    missed = tuple(sorted(leads - marked))
    chased_decoys = tuple(sorted(marked & decoys))
    chased_noise = tuple(sorted(marked - leads - decoys))

    wrong = len(chased_noise) + DECOY_WEIGHT * len(chased_decoys)

    if not leads:
        # crux D9: restraint is the whole measurement.
        recall = 1.0
        precision = 1.0 / (1.0 + wrong)
        marks_score = 100.0 * precision
    else:
        recall = len(found) / len(leads)
        denom = len(found) + wrong
        precision = (len(found) / denom) if denom else 0.0
        marks_score = 100.0 * _f1(precision, recall)

    if has_action:
        total = marks_score * (1.0 - ACTION_POINTS / 100.0)
        if action_ok:
            total += ACTION_POINTS
    else:
        total = marks_score

    return Score(
        found=found, missed=missed,
        chased_decoys=chased_decoys, chased_noise=chased_noise,
        recall=recall, precision=precision,
        marks=round(marks_score, 1),
        action_ok=action_ok if has_action else None,
        total=round(total, 1),
        no_lead=not leads,
        elapsed=elapsed,
    )
