"""proctor: a sitting, and the post-mortem over where the clock went.

**What this track is for.** The three skill tracks each ask whether you can do
a thing. None of them asks the question the exam actually turns on, which is
what you do when there is more work in front of you than clock behind you.
That decision has two halves and neither is taught anywhere: how much of the
budget a piece of work is entitled to, and when to walk away from one that is
not paying. `proctor` is those two halves and nothing else.

**How it is built, and why it is not a fourth engine.** A sitting schedules
scenarios that already exist and runs them through the engines that already
run them, using the same `on_done` seam chain mode introduced (crux D24). What
a sitting adds is a shared clock that does not stop, an allocation per leg, one
new verb (`X`, walk away), and an ending that ends the sitting when the budget
is gone rather than when the work runs out. That is the whole mechanism.

**The honesty this track owes, stated on its own intro screen.** crux cannot
make anyone sit twenty-four hours, and calling a forty-minute run an exam would
be the same class of lie as simulating a verification and reporting it as one
(crux D14). A compressed sitting trains allocation and abandonment. It does not
train endurance, and it does not pretend to.

**A sitting is one continuous run.** There is no resume: leaving by any route
ends it and records nothing for the legs you did not finish, which is also
exactly what walking out of an exam does. Each leg you *do* finish is recorded
as an ordinary attempt against its own scenario, tagged with the sitting, so
practice under the clock counts as practice and the pacing review can still
tell the two apart afterwards.
"""

from __future__ import annotations

from .. import pacing
from ..clock import Stopwatch, fmt
from ..config import PROCTOR
from ..model import Scenario, SittingBody
from ..render import Caps, Text, bar, line, wrap_rich
from ..session import Session
from ..state import Attempt
from . import POP, ScrollScreen, Screen, replace, set_pacer


def _short(seconds: float) -> str:
    """`26m`, or `95s` under two minutes. For the header only; every other
    place a duration is shown uses `clock.fmt`, which keeps both parts."""
    seconds = max(0.0, seconds)
    return f'{seconds:.0f}s' if seconds < 120 else f'{seconds / 60:.0f}m'


def _score_of(track: str, score) -> float:
    """0..100 out of whichever score type the leg's engine produced.

    sift and lineage both call it `total`; salvage and conduit call it
    `total_score` because their score is binary and the name says so. Ask for
    whichever the object has rather than branching per track, so a fifth engine
    following either convention needs no change here.
    """
    val = getattr(score, 'total', None)
    return val if val is not None else score.total_score


def _marked_of(score) -> tuple[str, ...]:
    """Reconstruct what was marked from a sift score.

    The `on_done` seam hands back a score and not the marks, and state.py is
    explicit that the marks are the evidence a wrong key can be re-scored
    against later. They are recoverable without widening the seam: every id a
    student marked is, by construction, either a lead they found, a decoy they
    chased or noise they chased, and the score carries all three.
    """
    found = getattr(score, 'found', ())
    return tuple(sorted(tuple(found)
                        + tuple(getattr(score, 'chased_decoys', ()))
                        + tuple(getattr(score, 'chased_noise', ()))))


# --------------------------------------------------------------------------
# The controller
# --------------------------------------------------------------------------

class Sitting:
    """Holds the clock, the allocations and the legs. Not a Screen.

    The same shape as `chain.Chain`, for the same reason: the legs are Screens
    the app stack owns, and this threads them together through the `on_done`
    closures it hands each one.
    """

    def __init__(self, session: Session, scenario: Scenario) -> None:
        self.session = session
        self.scenario = scenario
        self.body: SittingBody = scenario.body
        #: One scenario per slot, chosen unseen-first (see `pacing.fill`).
        #: Resolved once, up front, so the result screen can name a leg the
        #: clock never let you reach.
        self.picks = pacing.fill(self.body.slots, session.registry,
                                 session.state)
        self.allocs = pacing.allocations(
            [s.track for s in self.body.slots], self.body.budget)
        self.legs: list[pacing.Leg] = []
        #: The screen currently being played, which is the only one `X` acts
        #: on. A help page pushed above it is not a leg.
        self.current: Screen | None = None
        self.index = 0
        self.leg_start = 0.0
        #: Never paused. Time in your own editor is time on the exam clock,
        #: and a sitting whose clock stopped whenever you left the app would
        #: measure something nobody is graded on.
        self.watch = Stopwatch(session.clock)

    # -- the pacer contract ------------------------------------------------

    def owns(self, screen) -> bool:
        return screen is self.current

    def banner(self) -> str:
        """The header clock, coarse on purpose.

        It shares the top border with the scenario title, and the border gives
        the title away to make room for this (see `render.box_top`). Whole
        minutes buy that room back: nobody paces to the second with twenty
        minutes left, and under two minutes it goes back to seconds, because
        at that point the seconds are the whole message.
        """
        left = self.remaining
        if left <= 0:
            return 'budget gone'
        over = self.leg_overrun
        base = f'{_short(left)} left'
        return f'{base}  +{_short(over)}' if over > 0 else base

    def abandon(self):
        """`X`: take the zero, keep the clock. The verb the track is about."""
        return self._leg_done(self.index, None, abandoned=True)

    # -- clock -------------------------------------------------------------

    @property
    def remaining(self) -> float:
        return self.body.budget - self.watch.elapsed()

    @property
    def leg_elapsed(self) -> float:
        return self.watch.elapsed() - self.leg_start

    @property
    def leg_overrun(self) -> float:
        if self.index >= len(self.allocs):
            return 0.0
        return max(0.0, self.leg_elapsed - self.allocs[self.index])

    # -- flow --------------------------------------------------------------

    def begin(self):
        self.watch.start()
        set_pacer(self)
        return self.stage_screen(0)

    def stage_screen(self, i: int) -> Screen:
        """Build leg `i` with an `on_done` that reports back here."""
        self.index = i
        self.leg_start = self.watch.elapsed()
        pick = self.picks[i]
        done = lambda score, _i=i: self._leg_done(_i, score)
        if pick.track == 'sift':
            from .mark import MarkScreen
            screen = MarkScreen(self.session, pick, on_done=done)
        elif pick.track == 'salvage':
            from .salvage import SalvageScreen
            screen = SalvageScreen(self.session, pick, on_done=done)
        elif pick.track == 'lineage':
            from .lineage import WalkScreen
            screen = WalkScreen(self.session, pick, on_done=done)
        else:
            from .conduit import ConduitScreen
            screen = ConduitScreen(self.session, pick, on_done=done)
        self.current = screen
        return screen

    def _leg_done(self, i: int, score, abandoned: bool = False):
        pick = self.picks[i]
        elapsed = self.leg_elapsed
        value = 0.0 if (score is None or abandoned) else _score_of(pick.track, score)
        self.legs.append(pacing.Leg(
            scenario=pick.id, track=pick.track, title=pick.title,
            allocation=self.allocs[i], elapsed=elapsed, score=value,
            reached=True, abandoned=abandoned))
        self._record_leg(pick, score, elapsed, value, abandoned)
        self.current = None

        nxt = i + 1
        # The budget decides whether there is a next leg, not the work
        # remaining. That is the whole difference between a sitting and a
        # playlist.
        if nxt >= len(self.picks) or self.remaining <= 0:
            return self._finish()
        return replace(BetweenScreen(self, nxt))

    def _record_leg(self, pick: Scenario, score, elapsed: float, value: float,
                    abandoned: bool) -> None:
        """One ordinary attempt against the scenario, tagged with the sitting.

        Recorded against the real scenario rather than a sitting-local id
        because it *was* real practice: the marking was marked, the exploit was
        run against the real target. What the tag buys is the ability to answer
        "how do I play under a clock" separately afterwards, which is the whole
        point of storing it.
        """
        seed = getattr(self.current, 'seed', 0) or 0
        marked: tuple[str, ...] = ()
        recall = precision = 0.0
        action_ok = None
        runs, read_first = 0, None
        if score is not None:
            if pick.track == 'sift':
                marked = _marked_of(score)
                recall, precision = score.recall, score.precision
                action_ok = score.action_ok
            elif pick.track == 'lineage':
                # Recorded exactly as `session.record_walk` would, so a leg
                # played inside a sitting indexes identically to the same walk
                # played on its own: the route is the evidence, precision is
                # the share of the spend that was necessary.
                marked = tuple(e.id for e in score.taken)
                recall = 1.0 if score.reached else 0.0
                precision = (min(1.0, score.optimal / score.spent)
                             if score.spent else 0.0)
            else:
                # Same two numbers `session.record_run` stores, derived the
                # same way, so a leg played inside a sitting is indexed
                # identically to the same exercise played on its own.
                recall = 1.0 if score.landed else 0.0
                precision = (score.met / score.total) if score.total else 0.0
                runs, read_first = score.runs, score.read_first
        _save(self.session, Attempt(
            scenario=pick.id, track=pick.track,
            when=self.session.clock.wall(), elapsed=elapsed,
            total=round(value, 1), marks=round(value, 1),
            recall=recall, precision=precision,
            tier=pick.tier, seed=seed, marked=marked, action_ok=action_ok,
            runs=runs, read_first=read_first,
            sitting=self.scenario.id, abandoned=abandoned))

    def _finish(self):
        """Fill in the legs the clock never let you reach, then record."""
        for i in range(len(self.legs), len(self.picks)):
            pick = self.picks[i]
            self.legs.append(pacing.Leg(
                scenario=pick.id, track=pick.track, title=pick.title,
                allocation=self.allocs[i], reached=False))
        review = pacing.review(self.legs, self.body.budget, self.body.target,
                               spent=self.watch.elapsed())
        set_pacer(None)
        self.watch.pause()
        return replace(SittingResultScreen(self, review, self._record(review)))

    def _record(self, review: pacing.SittingReview) -> Attempt:
        """The sitting's own row. `precision` is the share of the clock that
        bought something, which is the one number worth carrying forward."""
        spent = review.spent or 1.0
        return _save(self.session, Attempt(
            scenario=self.scenario.id, track=PROCTOR,
            when=self.session.clock.wall(), elapsed=review.spent,
            total=round(review.score, 1), marks=round(review.score, 1),
            recall=len(review.landed) / max(1, len(review.legs)),
            precision=max(0.0, 1.0 - review.sunk / spent),
            tier=self.scenario.tier, seed=0, marked=(),
            sitting=self.scenario.id))


def _save(session: Session, attempt: Attempt) -> Attempt:
    session.state.record(attempt)
    session._save()
    return attempt


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------

class SittingIntroScreen(Screen):
    """The brief, the budget, the target, and what a sitting is not."""

    help_topic = PROCTOR
    status = 'sitting'

    def __init__(self, session: Session, scenario: Scenario) -> None:
        self.session = session
        self.scenario = scenario
        self.body_data: SittingBody = scenario.body
        self.picks = pacing.fill(self.body_data.slots, session.registry,
                                 session.state)
        self.allocs = pacing.allocations(
            [s.track for s in self.body_data.slots], self.body_data.budget)

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def unfillable(self) -> bool:
        return any(p is None for p in self.picks)

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        b = self.body_data
        rows = wrap_rich(caps, b.brief, caps.cols - 6, '  ', p.fg, p.accent)
        rows.append(Text())

        head = Text().add('  ')
        head.add(fmt(b.budget), p.accent, bold=True)
        head.add(f' for {len(b.slots)} leg'
                 f'{"" if len(b.slots) == 1 else "s"}, and you pass on ', p.fg)
        head.add(f'{b.target:.0f}', p.accent, bold=True)
        head.add('.', p.fg)
        rows.append(head)
        rows.append(Text())

        for i, (slot, pick) in enumerate(zip(b.slots, self.picks)):
            row = Text().add('    ')
            row.add(f'{slot.track:<9}', p.info)
            title = pick.title if pick is not None else '(nothing available)'
            room = max(10, caps.cols - 6 - 9 - 12)
            if len(title) > room:
                title = title[:room - 1] + caps.g('ellipsis')
            row.add(title, p.fg if pick is not None else p.err)
            row.pad_to(caps.cols - 2 - 10)
            row.add(f'{fmt(self.allocs[i]):>9}', p.dim)
            rows.append(row)

        rows.append(Text())
        rows.extend(wrap_rich(
            caps,
            'The share on the right is what each leg is **entitled to**, not '
            'how long it takes. Cross it and you are spending the next leg\'s '
            'time. **X** walks away from a leg and keeps the clock.',
            caps.cols - 6, '  ', p.muted, p.accent))
        rows.append(Text())
        rows.extend(wrap_rich(
            caps,
            'This is a **compressed** sitting. crux cannot make you sit '
            'twenty-four hours and does not pretend to: what it trains is the '
            'allocation and the walking away. Endurance is not on offer here.',
            caps.cols - 6, '  ', p.warn, p.accent))
        rows.append(Text())
        if self.unfillable:
            rows.append(line('  A leg has no scenario available on this '
                             'machine. Install what is missing, or play a '
                             'different sitting.', p.err))
        else:
            rows.append(line('  The clock starts when you press enter, and it '
                             'does not stop.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        out = [] if self.unfillable else [(caps.g('enter'), 'start the clock')]
        return out + [('esc', 'back'), ('q', 'quit'), ('?', 'help')]

    def handle(self, key):
        if key.name == 'RET' and not self.unfillable:
            return replace(Sitting(self.session, self.scenario).begin())
        return super().handle(key)


class BetweenScreen(Screen):
    """Between two legs: what the last one cost, and what is left.

    Deliberately thin. A full debrief belongs to standalone practice; here the
    only thing worth reading is the clock, because the only decision available
    is how to spend the rest of it.
    """

    help_topic = PROCTOR

    def __init__(self, sitting: Sitting, index: int) -> None:
        self.sitting = sitting
        self.index = index

    @property
    def title(self) -> str:
        return self.sitting.scenario.title

    @property
    def status(self) -> str:
        return f'leg {self.index + 1} of {len(self.sitting.picks)}'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.sitting
        last = s.legs[-1]

        good = last.paid
        row = Text().add('  ')
        row.add(caps.g('check') if good else caps.g('cross'),
                p.ok if good else p.warn)
        row.add(f' {last.title}', p.fg)
        rows = [row]

        cost = Text().add('    ')
        cost.add(f'{fmt(last.elapsed)}', p.fg)
        cost.add(f' of its {fmt(last.allocation)} share', p.muted)
        if last.overrun:
            cost.add(f'   over by {fmt(last.overrun)}', p.warn)
        if last.abandoned:
            cost.add('   walked away', p.info)
        rows.append(cost)
        rows.append(Text())

        left = s.remaining
        clock = Text().add('  ')
        clock.spans.extend(bar(caps, max(0.0, left) / s.body.budget, 18).spans)
        clock.add(f'  {fmt(max(0.0, left))} left', p.ok if left > 0 else p.err,
                  bold=True)
        rows.append(clock)
        rows.append(Text())

        nxt = s.picks[self.index]
        n = Text().add('  Next: ')
        n.add(f'{nxt.track} ', p.info)
        n.add(nxt.title, p.fg)
        n.add(f'   share {fmt(s.allocs[self.index])}', p.dim)
        rows.append(n)
        remaining_legs = len(s.picks) - self.index
        if left > 0 and remaining_legs > 1:
            per = left / remaining_legs
            rows.append(line(f'  {remaining_legs} legs left and {fmt(left)} to '
                             f'spend: {fmt(per)} each from here.', p.muted))
        rows.append(Text())
        rows.append(line('  Press enter. The clock has not stopped.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [(caps.g('enter'), 'continue'), ('H', 'home'), ('q', 'quit'),
                ('?', 'help')]

    def handle(self, key):
        if key.name == 'RET':
            return replace(self.sitting.stage_screen(self.index))
        return super().handle(key)


def _leg_table(caps: Caps, legs, palette) -> list[Text]:
    """The legs, one row each: what it was entitled to, what it took, and
    what came of it. The three columns are the whole argument of the track."""
    p = palette
    rows = [line(f'  {"leg":<30}{"share":>8}{"took":>9}   what came of it',
                 p.muted)]
    for leg in legs:
        title = leg.title
        if len(title) > 29:
            title = title[:28] + caps.g('ellipsis')
        row = Text().add('  ')
        row.add(f'{title:<30}', p.fg if leg.reached else p.dim)
        row.add(f'{fmt(leg.allocation):>8}', p.dim)
        took = fmt(leg.elapsed) if leg.reached else '-'
        over = leg.overrun > 0
        row.add(f'{took:>9}', p.warn if over else p.muted)
        colour = (p.ok if leg.paid else
                  p.info if leg.abandoned else
                  p.dim if not leg.reached else p.err)
        row.add(f'   {leg.verdict}', colour)
        rows.append(row)
    return rows


class SittingResultScreen(ScrollScreen):
    """The post-mortem. The score is the small half of this screen."""

    help_topic = PROCTOR

    def __init__(self, sitting: Sitting, review: pacing.SittingReview,
                 attempt: Attempt) -> None:
        super().__init__()
        self.sitting = sitting
        self.review = review
        self.attempt = attempt
        self.body_data: SittingBody = sitting.scenario.body

    @property
    def title(self) -> str:
        return self.sitting.scenario.title

    @property
    def status(self) -> str:
        r = self.review
        return f'{r.score:.0f}  {"pass" if r.passed else "short"}'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        r = self.review
        rows: list[Text] = []

        head = Text().add('  ')
        head.spans.extend(bar(caps, r.score / 100.0, 18).spans)
        head.add(f'  {r.score:.0f}', p.ok if r.passed else p.warn, bold=True)
        head.add(f' of {r.target:.0f}', p.dim)
        head.add(f'   {fmt(r.spent)} of {fmt(r.budget)}', p.dim)
        rows.append(head)
        rows.extend(wrap_rich(caps, r.headline(), caps.cols - 6, '  ',
                              p.ok if r.passed else p.warn, p.accent))
        rows.append(Text())

        rows.extend(_leg_table(caps, r.legs, p))
        rows.append(Text())

        rows.append(line('  Where the clock went', p.accent, bold=True))
        for label, value, colour in (
                ('in the exercises', fmt(r.on_legs), p.muted),
                ('reading between them', fmt(max(0.0, r.spent - r.on_legs)), p.muted),
                ('past your own allocation', fmt(r.overrun),
                 p.warn if r.overrun else p.muted),
                ('sunk: past allocation, paid nothing', fmt(r.sunk),
                 p.err if r.sunk else p.ok),
                ('unspent', fmt(r.banked), p.ok if r.banked else p.muted)):
            row = Text().add(f'    {label:<38}', p.muted)
            row.add(value, colour, bold=label.startswith('sunk') and bool(r.sunk))
            rows.append(row)
        rows.append(Text())

        rows.append(line('  What that means', p.accent, bold=True))
        for note in r.notes():
            rows.extend(wrap_rich(caps, note, caps.cols - 8, '    ', p.muted,
                                  p.accent))
        rows.append(Text())

        if self.body_data.debrief:
            rows.append(line('  The habit', p.accent, bold=True))
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))
        if self.sitting.session.save_error:
            rows.append(line(f'  history not saved: '
                             f'{self.sitting.session.save_error}', p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)


class PacingScreen(ScrollScreen):
    """The standalone review: every attempt ever recorded, not one sitting.

    Reachable from the proctor track with `p`. It reads history and nothing
    else, so it is worth opening before a sitting as well as after one: the
    per-track medians are what a realistic allocation would be built from, and
    the zero-scoring time is the same measurement a sitting makes, taken over
    everything you have ever played here.
    """

    help_topic = PROCTOR
    title = 'pacing review'

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.review = pacing.history(session.state.attempts)

    @property
    def status(self) -> str:
        r = self.review
        return f'{r.attempts} attempt{"" if r.attempts == 1 else "s"}'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        r = self.review
        rows: list[Text] = []

        if not r.any:
            rows.append(line('  Nothing recorded yet.', p.warn, bold=True))
            rows.append(Text())
            rows.extend(wrap_rich(
                caps,
                'Play a few scenarios, or sit a sitting, and this becomes a '
                'picture of where your clock actually goes: how long each '
                'track costs you, and how much of that time came back with '
                'nothing.', caps.cols - 6, '  ', p.muted, p.accent))
            return rows

        head = Text().add('  ')
        head.add(fmt(r.total_time), p.accent, bold=True)
        head.add(' on task across ', p.fg)
        head.add(f'{r.attempts}', p.accent, bold=True)
        head.add(' attempt' + ('' if r.attempts == 1 else 's'), p.fg)
        if r.sittings:
            head.add(f'   {r.sittings} sitting'
                     f'{"" if r.sittings == 1 else "s"}', p.info)
        rows.append(head)
        rows.append(Text())

        rows.append(line(f'  {"track":<10}{"runs":>6}{"median":>9}'
                         f'{"longest":>9}{"on task":>10}{"zeros":>7}'
                         f'{"cost":>9}', p.muted))
        for t in r.tracks:
            row = Text().add(f'  {t.track:<10}', p.fg)
            if not t.attempts:
                row.add(f'{"-":>6}{"-":>9}{"-":>9}{"-":>10}{"-":>7}{"-":>9}',
                        p.dim)
                rows.append(row)
                continue
            row.add(f'{t.attempts:>6}', p.muted)
            med = fmt(t.median) if t.completed else '-'
            row.add(f'{med:>9}', p.dim if t.thin else p.fg)
            row.add(f'{fmt(t.longest):>9}', p.muted)
            row.add(f'{fmt(t.on_task):>10}', p.muted)
            row.add(f'{t.zeros:>7}', p.warn if t.zeros else p.muted)
            row.add(f'{fmt(t.zero_time):>9}', p.err if t.zero_time else p.muted)
            rows.append(row)
        rows.append(Text())
        rows.append(line('  "zeros" is attempts that scored nothing, "cost" is '
                         'what they took.', p.dim))
        rows.append(Text())

        rows.append(line('  What that means', p.accent, bold=True))
        for note in r.notes():
            rows.extend(wrap_rich(caps, note, caps.cols - 8, '    ', p.muted,
                                  p.accent))

        if r.abandons:
            rows.append(Text())
            rows.append(line(f'  You have walked away from {r.abandons} leg'
                             f'{"" if r.abandons == 1 else "s"} inside a '
                             f'sitting.', p.info))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])
