"""lineage: walk a domain, and pay for every right you use.

**Two screens, because reading and moving are two different acts.** `m` opens
the collection: every principal and every right, whether or not you can use it,
which is what a collection *is*. Esc comes back to the moves. Splitting them is
not a layout preference, it is the exercise: if the only thing on screen were
the rights you can use right now, the choice would be made blind and the answer
would be a guess. A student has to be able to look at the whole map, work out
where they are trying to end up, and only then spend something. That is also
exactly what the job looks like.

**Group membership is not a move.** Owning a principal owns every group it
nests into, applied as a closure and shown in what you hold. See `lineage.py`
for why; the visible consequence is that the list of moves only ever contains
rights that cost something.

**The budget is computed from the graph, not authored.** Twice the cheapest
route: enough to survive one real mistake and not two. A student who takes the
expensive route still arrives and still scores, which is the point of the whole
track. Arriving is not the only thing being measured.
"""

from __future__ import annotations

from .. import lineage as LN
from ..clock import Stopwatch, fmt
from ..model import LineageBody, Scenario
from ..provenance import based_on
from ..render import Caps, Text, bar, line, wrap_rich
from ..session import Session
from . import POP, STAY, ListScreen, ScrollScreen, Screen, push, replace, selector


def _kind_mark(kind: str) -> str:
    """One short word per principal kind. Not a glyph: `computer` and `group`
    have to be told apart at the ASCII rung, where every clever symbol becomes
    the same asterisk."""
    return {'user': 'user', 'group': 'group', 'computer': 'host',
            'domain': 'domain'}.get(kind, kind)


class WalkScreen(ListScreen):
    """The moves. Each row is a right you can use and what it costs."""

    help_topic = 'lineage'

    def __init__(self, session: Session, scenario: Scenario,
                 seed: int | None = None, on_done=None) -> None:
        super().__init__()
        self.session = session
        self.scenario = scenario
        self.on_done = on_done
        self.body_data: LineageBody = scenario.body
        if seed is None:
            seed = session.seed_override
        self.seed = (seed if seed is not None
                     else int(session.clock.wall() * 1000) & 0xFFFFFFFF)
        self.built = self.body_data.build(self.seed)
        #: Solved once, up front. The cheapest route is the key this attempt
        #: is graded against, and recomputing it per keypress would let a
        #: rounding difference between two calls change the score mid-walk.
        self.best = LN.cheapest(self.built)
        self.budget = LN.budget_for(self.best.cost)
        self.taken: list = []
        self.gave_up = False
        self.watch = Stopwatch(session.clock)
        self.watch.start()
        self._done = False

    # -- state -------------------------------------------------------------

    @property
    def owned(self) -> frozenset[str]:
        return LN.closure(set(self.built.owned) | {e.dst for e in self.taken},
                          self.built.edges)

    @property
    def spent(self) -> int:
        return sum(LN.cost_of(e.kind) for e in self.taken)

    @property
    def left(self) -> int:
        return self.budget - self.spent

    @property
    def arrived(self) -> bool:
        return self.built.objective in self.owned

    def moves(self) -> tuple:
        return LN.available(self.built, self.owned)

    # -- framing -----------------------------------------------------------

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        return f'{self.spent} of {self.budget} spent'

    def count(self) -> int:
        return len(self.moves())

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows: list[Text] = []
        label = based_on(self.scenario.source)
        if label:
            rows.append(line(f'  {label}', p.dim))
        rows.extend(wrap_rich(caps, self.body_data.brief, caps.cols - 6, '  ',
                              p.fg, p.accent))

        obj = Text().add('  Objective: ', p.muted)
        obj.add(self.built.label(self.built.objective), p.accent2, bold=True)
        rows.append(obj)

        held = sorted(self.owned, key=lambda n: self.built.label(n))
        hold = Text().add('  You hold: ', p.muted)
        shown = 0
        for nid in held:
            piece = self.built.label(nid)
            if hold.width() + len(piece) + 3 > caps.cols - 12:
                hold.add(f'  +{len(held) - shown} more', p.dim)
                break
            if shown:
                hold.add('   ', p.dim)
            hold.add(piece, p.ok)
            shown += 1
        rows.append(hold)
        rows.append(Text())

        # Hand-holding on first contact, and out of the way after. A priced
        # graph is a genuinely new idea the first time you meet it (what is
        # the number, why do I hold groups I did not pick, what does a move
        # do), so the first time the player opens any lineage scenario they
        # get the whole mechanic spelled out. Once they have finished one it
        # collapses to a single reminder line, the same shape the sift screen
        # uses. Gated on standalone lineage history, so a chain's lineage
        # stage still explains itself to someone who has never played the
        # track.
        first_time = self.session.state.track_summary('lineage')[0] == 0
        if first_time:
            rows.append(line('  New here?', p.accent2, bold=True))
            rows.extend(wrap_rich(
                caps,
                'Each row below is a **right** you can use now; the `[n]` is '
                'what using it costs. **enter** takes it, and new rights open '
                'up. Reach the **objective** above for the fewest total '
                'points, which is rarely the fewest steps. You already hold '
                'everything under "You hold", and its groups, for free. '
                '**m** shows the whole map, **?** explains more.',
                caps.cols - 6, '  ', p.muted, p.accent))
        else:
            rows.extend(wrap_rich(
                caps,
                'Each row is a right you can use; `[n]` is its cost. enter '
                'takes one, m reads the whole collection.',
                caps.cols - 6, '  ', p.muted, p.accent))
        rows.append(Text())
        return rows

    def empty_state(self, caps: Caps) -> list[Text]:
        return [line('  Nothing left that you can use. Press g to see the '
                     'route you did not take.', caps.palette.warn)]

    def blocks(self, caps: Caps) -> list[list[Text]]:
        """One row per move, plus a line of explanation under the cursor.

        The explanation is on the selected row only. Printing it against every
        move would turn a list of eight into a wall of twenty-four and bury
        the thing being compared, which is the number in the brackets.
        """
        p = caps.palette
        out: list[list[Text]] = []
        for i, e in enumerate(self.moves()):
            sel = i == self.cursor
            cost = LN.cost_of(e.kind)
            affordable = cost <= self.left
            t = selector(caps, sel)
            t.add(f'[{cost}] ', p.ok if cost <= 1 else
                  p.warn if cost <= 2 else p.err, bold=True)
            t.add(f'{self.built.label(e.src)} ', p.muted)
            t.add(f'{e.kind} ', p.accent if sel else p.fg, bold=sel)
            t.add(self.built.label(e.dst), p.fg if affordable else p.dim)
            if not affordable:
                t.add('   more than you have left', p.dim)
            block = [t]
            if sel:
                meaning = LN.EDGE_MEANING.get(e.kind, '')
                if meaning:
                    block.extend(wrap_rich(caps, meaning, caps.cols - 12,
                                           '       ', p.muted, p.accent))
            out.append(block)
        return out

    # -- input -------------------------------------------------------------

    def extra_hints(self) -> list[tuple[str, str]]:
        return [('m', 'collection'), ('g', 'give up')]

    def activate(self, index: int):
        moves = self.moves()
        if index >= len(moves):
            return STAY
        edge = moves[index]
        if LN.cost_of(edge.kind) > self.left:
            return STAY
        self.taken.append(edge)
        self.cursor = 0
        if self.arrived or not self.left or not self.moves():
            return self._finish()
        return STAY

    def handle(self, key):
        if key.name == 'm' and not key.ctrl:
            return push(MapScreen(self))
        if key.name == 'g' and not key.ctrl:
            self.gave_up = True
            return self._finish()
        return super().handle(key)

    def _finish(self):
        self._done = True
        self.watch.pause()
        score = LN.score_walk(self.built, self.taken,
                              reached=self.arrived and not self.gave_up,
                              optimal=self.best.cost, budget=self.budget,
                              elapsed=self.watch.elapsed())
        if self.on_done is not None:
            return self.on_done(score)
        self.session.record_walk(self.scenario, score,
                                 tuple(e.id for e in self.taken), self.seed)
        return replace(WalkResultScreen(self, score))

    def close(self) -> None:
        if not self._done:
            self.watch.pause()


class MapScreen(ScrollScreen):
    """The whole collection: every principal, and every right out of it.

    Unfiltered on purpose. Hiding the rights you cannot use yet would hide the
    reason to buy the one that unlocks them, and reading ahead is the entire
    skill. What is marked is only what you currently hold, because that is a
    fact about you rather than about the domain.
    """

    help_topic = 'lineage'
    status = 'the collection'

    def __init__(self, walk: WalkScreen) -> None:
        super().__init__()
        self.walk = walk

    @property
    def title(self) -> str:
        return f'{self.walk.built.domain}'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        b = self.walk.built
        owned = self.walk.owned
        rows: list[Text] = [
            line(f'  {len(b.nodes)} principals, '
                 f'{len(b.edges)} rights between them.', p.muted),
            line('  A principal you hold is marked. Esc goes back to the '
                 'moves.', p.dim),
            Text()]

        order = {'domain': 0, 'group': 1, 'computer': 2, 'user': 3}
        for n in sorted(b.nodes, key=lambda x: (order.get(x.kind, 9), x.name)):
            head = Text().add('  ')
            head.add(caps.g('check') + ' ' if n.id in owned else '  ',
                     p.ok)
            head.add(n.name, p.accent if n.id in owned else p.fg,
                     bold=n.id == b.objective)
            head.pad_to(max(30, caps.cols - 30))
            head.add(f'{_kind_mark(n.kind):<9}', p.dim)
            if n.id == b.objective:
                head.add('the objective', p.accent2)
            elif n.note:
                head.add(n.note, p.muted)
            rows.append(head)
            for e in sorted(b.out_of(n.id), key=lambda x: x.kind):
                cost = LN.cost_of(e.kind)
                r = Text().add('        ')
                r.add(f'[{cost}] ' if cost else '[-] ',
                      p.dim if not cost else
                      p.ok if cost <= 1 else p.warn if cost <= 2 else p.err)
                r.add(f'{e.kind} ', p.info)
                r.add(caps.g('arrow'), p.dim)
                r.add(f' {b.label(e.dst)}', p.fg)
                rows.append(r)
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back to the moves'), ('q', 'quit'), ('?', 'help')])


def _route(caps: Caps, built, edges, palette, show_cost: bool = True) -> list[Text]:
    """One route, step by step. Free steps are shown and priced at nothing,
    because leaving them out would make a four-hop route look like two."""
    p = palette
    rows: list[Text] = []
    for e in edges:
        cost = LN.cost_of(e.kind)
        r = Text().add('    ')
        if show_cost:
            r.add(f'[{cost}] ' if cost else '[-] ',
                  p.dim if not cost else
                  p.ok if cost <= 1 else p.warn if cost <= 2 else p.err)
        r.add(f'{built.label(e.src)} ', p.muted)
        r.add(e.kind, p.info)
        r.add(f' {built.label(e.dst)}', p.fg)
        rows.append(r)
    return rows


class WalkResultScreen(ScrollScreen):
    """What your route cost, what the cheapest one was, and why they differ."""

    help_topic = 'lineage'

    def __init__(self, walk: WalkScreen, score: LN.WalkScore) -> None:
        super().__init__()
        self.walk = walk
        self.score = score
        self.built = walk.built
        self.body_data: LineageBody = walk.scenario.body

    @property
    def title(self) -> str:
        return self.walk.scenario.title

    @property
    def status(self) -> str:
        return f'{self.score.total:.0f}  {self.score.band}'

    def _verdict(self) -> str:
        s = self.score
        if self.walk.gave_up:
            return 'You gave up. The cheapest route is below.'
        if not s.reached:
            return (f'You ran out of budget {s.left} short of it, having '
                    f'spent {s.spent}.')
        if not s.overspend:
            return ('You arrived on the cheapest route there was, and paid '
                    'nothing you did not have to.')
        return (f'You arrived, and it cost {s.spent} where {s.optimal} would '
                f'have done.')

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self.score
        b = self.built
        rows: list[Text] = []

        head = Text().add('  ')
        head.spans.extend(bar(caps, s.total / 100.0, 18).spans)
        head.add(f'  {s.total:.0f}', p.ok if s.total >= 70 else p.warn,
                 bold=True)
        head.add(f'   spent {s.spent} of {s.budget}', p.dim)
        head.add(f'   {fmt(s.elapsed)}', p.dim)
        rows.append(head)
        rows.extend(wrap_rich(caps, self._verdict(), caps.cols - 6, '  ',
                              p.ok if s.reached and not s.overspend else p.warn,
                              p.accent))
        rows.append(Text())

        if s.taken:
            rows.append(line('  What you used', p.accent, bold=True))
            rows.extend(_route(caps, b, s.taken, p))
            rows.append(Text())

        if s.dead_ends:
            rows.append(line('  What you paid for that went nowhere',
                             p.warn, bold=True))
            for e in s.dead_ends:
                rows.append(line(f'    {b.label(e.dst)}  '
                                 f'({LN.cost_of(e.kind)})', p.err))
                if e.why:
                    rows.extend(wrap_rich(caps, e.why, caps.cols - 12,
                                          '        ', p.muted, p.accent))
            rows.append(Text())

        rows.append(line(f'  The cheapest route, at {self.walk.best.cost}',
                         p.accent, bold=True))
        rows.extend(_route(caps, b, self.walk.best.edges, p))
        for e in self.walk.best.edges:
            if e.why:
                rows.extend(wrap_rich(caps, f'**{e.kind}**: {e.why}',
                                      caps.cols - 10, '      ', p.muted,
                                      p.accent))
        rows.append(Text())

        # The claim the track is built on, but only where this graph has it.
        hops = LN.shortest(b)
        if hops.reachable and hops.cost > self.walk.best.cost:
            rows.append(line('  What a map that counts edges would have drawn',
                             p.accent2, bold=True))
            rows.extend(_route(caps, b, hops.edges, p))
            rows.extend(wrap_rich(
                caps,
                f'**{hops.hops} edges against {self.walk.best.hops}**, and it '
                f'costs {hops.cost} rather than {self.walk.best.cost}. Fewer '
                f'hops is not cheaper. It is just fewer hops.',
                caps.cols - 8, '    ', p.muted, p.accent))
            rows.append(Text())

        if self.body_data.debrief:
            rows.append(line('  The habit', p.accent, bold=True))
            rows.extend(wrap_rich(caps, self.body_data.debrief, caps.cols - 6,
                                  '  ', p.muted, p.accent))

        if self.walk.scenario.waypoint:
            rows.append(Text())
            rows.append(line(f'  Waypoint node: '
                             f'{self.walk.scenario.waypoint}', p.dim))
        if self.walk.session.save_error:
            rows.append(line(f'  history not saved: '
                             f'{self.walk.session.save_error}', p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return (self.scroll_hints(caps)
                + [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')])

    def handle(self, key):
        if key.name == 'RET':
            return POP
        return super().handle(key)
