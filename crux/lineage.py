"""The arithmetic behind `lineage`: what a right costs, and what the path is.

Pure functions over an authored graph. Nothing here renders, nothing reads a
clock (crux D17), and nothing knows what a screen is. The engine can therefore
be asked the one question that makes the content trustworthy, which is the same
question `validate.py` asks of every `salvage` script: **is this actually
solvable, and by what?**

**The claim this track makes, and the whole reason it is not `sift` with a
graph in it.** A collection tool will draw you the shortest path to Domain
Admin. The shortest path is a count of edges, and an edge is not a unit of
anything: `ForceChangePassword` and `MemberOf` are one hop each, and one of
them is free while the other means you have changed a real person's password
and somebody is now on the phone to a help desk. **So `lineage` prices the
edges**, and the cheapest path is frequently not the shortest one. Reading a
graph and picking the route that is cheapest rather than shortest is the
judgement; the graph itself is just where it happens.

**The prices, and where they come from.** They are not a claim about
difficulty. They are a rough claim about **what using the right costs you on an
engagement**: how much noise it makes, how much of it is irreversible, and how
much somebody notices. A membership you already have costs nothing because it
is not an action. Connecting to a host you are admin on costs one, because it
is one connection. Pulling credentials out of a host's memory costs two,
because that is the single most-watched thing an operator can do. Changing a
real user's password costs four, because it is destructive, it is loud, and it
is the one on this list that will get a client on the phone. Somebody will
disagree with the exact numbers; the point of having them at all is that
without them a graph teaches "follow the highlighted line", which is the
instinct that walks people straight through a password reset they did not need.

**`MemberOf` is free and automatic, and that is a modelling decision worth
stating.** You do not "use" a group membership; you either have it or you do
not, and it is transitive. So owning a principal owns every group it is
transitively a member of, applied as a closure rather than offered as a move.
The alternative, making the student click through zero-cost edges, adds
keystrokes and removes nothing. What it would have taught, that you often
already hold more than you think, is better taught by showing the closed set of
what you own, which is what the screen does.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

#: Rights that are a state rather than an action: free, transitive, and
#: applied by closure rather than chosen.
FREE = ('MemberOf',)

#: Rights whose use **writes to the directory**. The distinction is not
#: cosmetic and it is not the same as the price: a write leaves an object
#: changed, an event on a domain controller, and something a defender can
#: query for afterwards, while reading a password out of an attribute you were
#: granted leaves nothing at all. Two routes can cost the same and differ
#: entirely on this, which is why a scenario can be authored to teach it
#: (`teaches="quiet"`) and `validate.py` can check the claim.
WRITES = ('AddMember', 'GenericAll', 'GenericWrite', 'AllExtendedRights',
          'AllowedToDelegate', 'AllowedToAct', 'WriteDacl', 'Owns',
          'WriteOwner', 'ForceChangePassword')


def writes(kind: str) -> bool:
    return kind in WRITES

#: What using a right costs on an engagement. See the module docstring for the
#: reasoning; the ordering matters more than the absolute values.
EDGE_COST = {
    'MemberOf': 0,
    'AdminTo': 1,
    'CanRDP': 1,
    'CanPSRemote': 1,
    'SQLAdmin': 1,
    'DCSync': 1,
    'ReadLAPSPassword': 1,
    'ReadGMSAPassword': 1,
    'HasSession': 2,
    'AddMember': 2,
    'GenericAll': 2,
    'GenericWrite': 2,
    'AllExtendedRights': 2,
    'AllowedToDelegate': 2,
    'AllowedToAct': 2,
    'WriteDacl': 2,
    'Owns': 2,
    'WriteOwner': 3,
    'ForceChangePassword': 4,
}

#: One line on what the right is and what using it takes. Shown against the
#: move, because a price nobody can see the reasoning for is a price nobody
#: learns anything from.
EDGE_MEANING = {
    'MemberOf': 'a membership you already hold. Free, and it carries through '
                'nested groups whether you noticed or not',
    'AdminTo': 'local administrator on that host. One connection',
    'CanRDP': 'an interactive desktop on that host',
    'CanPSRemote': 'a remote shell on that host',
    'SQLAdmin': 'administrator inside the database instance, and usually a '
                'command shell from there',
    'DCSync': 'replicate the directory and take every hash in it. One command '
              'and the domain is over',
    'ReadLAPSPassword': 'read the local administrator password out of the '
                        'directory. Nothing is written and nothing breaks',
    'ReadGMSAPassword': 'read a managed service account password out of the '
                        'directory',
    'HasSession': 'a session to steal credentials from, which means touching '
                  'a live host memory. The most-watched thing you can do',
    'AddMember': 'add yourself to the group. Reversible, but you have written '
                 'to the directory and it is in a log',
    'GenericAll': 'full control. Over a user that means writing a service '
                  'principal name and cracking the ticket offline, which is '
                  'why it prices under a password reset: more control buys '
                  'you quieter options, not louder ones',
    'GenericWrite': 'write its attributes: a service principal name to roast, '
                    'or a logon script to run',
    'AllExtendedRights': 'the extended rights, password reset among them',
    'AllowedToDelegate': 'impersonate anyone to that service',
    'AllowedToAct': 'configure delegation onto that host and impersonate into '
                    'it',
    'WriteDacl': 'rewrite the object permissions, then grant yourself what '
                 'you need. Two steps, and the second is the loud one',
    'Owns': 'you own the object, so you can grant yourself its permissions',
    'WriteOwner': 'take ownership first, then grant, then use. Three writes '
                  'and a changed owner somebody will query',
    'ForceChangePassword': 'reset a real person password. Destructive, loud, '
                           'and the one on this list that ends in a phone '
                           'call to a help desk',
}

#: How much clock a sitting gets is authored; how much budget a walk gets is
#: computed, because it is a property of the graph rather than of the author.
#: Twice the cheapest route, floored so a very short graph is not brutal: you
#: can afford one real mistake and not two, which is the tension the track
#: needs. Authoring it per scenario was rejected for the obvious reason, that
#: it would drift from the graph the moment an edge moved.
BUDGET_FACTOR = 2.0
BUDGET_FLOOR = 2


def cost_of(kind: str) -> int:
    return EDGE_COST.get(kind, 1)


def budget_for(optimal: int) -> int:
    return max(optimal + BUDGET_FLOOR, math.ceil(optimal * BUDGET_FACTOR))


# --------------------------------------------------------------------------
# Ownership
# --------------------------------------------------------------------------

def closure(owned, edges) -> frozenset[str]:
    """Everything you hold, including every group it nests into.

    Fixed point rather than a single pass: nested groups nest, and a domain
    where `TIER2 SUPPORT` is inside `WORKSTATION ADMINS` is not an edge case,
    it is the normal shape and the reason people miss what they already have.
    """
    have = set(owned)
    free = [e for e in edges if e.kind in FREE]
    changed = True
    while changed:
        changed = False
        for e in free:
            if e.src in have and e.dst not in have:
                have.add(e.dst)
                changed = True
    return frozenset(have)


def available(built, owned) -> tuple:
    """The moves worth offering: priced rights out of what you hold, into
    something you do not already hold.

    Free rights are not offered because they are not moves, and a right into a
    principal you already own is not offered because it buys nothing. Hiding
    the second is not a kindness: an option that cannot change the state is
    noise, and this track has enough real noise in it already.
    """
    have = closure(owned, built.edges)
    out = [e for e in built.edges
           if e.kind not in FREE and e.src in have and e.dst not in have]
    # Cheapest first, then by target name, so the list has an order a person
    # can hold in their head. Not by "usefulness": ranking the moves by how
    # much they help would be doing the exercise for them.
    return tuple(sorted(out, key=lambda e: (cost_of(e.kind),
                                            built.label(e.dst), e.kind)))


# --------------------------------------------------------------------------
# Solving
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Path:
    """A route through the graph, priced."""

    edges: tuple
    cost: int
    reachable: bool = True

    @property
    def hops(self) -> int:
        """Every edge, free ones included. This is the number a collection
        tool's 'shortest path' would show you, which is the whole point of
        keeping it next to `cost`."""
        return len(self.edges)

    @property
    def priced(self) -> tuple:
        return tuple(e for e in self.edges if e.kind not in FREE)


_UNREACHABLE = Path(edges=(), cost=0, reachable=False)


def _search(built, key, owned=None, target=None) -> Path:
    """Dijkstra from everything you hold, minimising `key` over the edges.

    One search function for every question the track asks. The cheapest route
    and the shortest route differ only in what an edge is worth: pass the price
    and you get the cheapest, pass 1 and you get the fewest hops. Writing them
    as two functions was the first version and the two immediately drifted on
    how they treated free edges. `target` defaults to the scenario objective
    but can be any node, which is what lets a checker ask "how far to *there*"
    without a second search written a different way.
    """
    start = set(owned) if owned is not None else set(built.owned)
    goal = target if target is not None else built.objective
    if goal in start:
        return Path(edges=(), cost=0)

    best: dict[str, float] = {n: 0.0 for n in start}
    prev: dict[str, tuple] = {}
    queue: list[tuple[float, str]] = [(0.0, n) for n in sorted(start)]
    heapq.heapify(queue)
    by_src: dict[str, list] = {}
    for e in built.edges:
        by_src.setdefault(e.src, []).append(e)

    while queue:
        dist, node = heapq.heappop(queue)
        if dist > best.get(node, float('inf')):
            continue
        if node == goal:
            break
        for e in by_src.get(node, ()):
            step = dist + key(e)
            if step < best.get(e.dst, float('inf')):
                best[e.dst] = step
                prev[e.dst] = (node, e)
                heapq.heappush(queue, (step, e.dst))

    if goal not in best:
        return _UNREACHABLE

    chain: list = []
    at = goal
    while at in prev:
        at, edge = prev[at]
        chain.append(edge)
    chain.reverse()
    return Path(edges=tuple(chain),
                cost=sum(cost_of(e.kind) for e in chain))


def cheapest(built, owned=None) -> Path:
    """The route that costs least. This is the answer the track grades on."""
    return _search(built, lambda e: cost_of(e.kind), owned)


def shortest(built, owned=None) -> Path:
    """The route with fewest edges: what a collection tool would draw.

    Kept because the gap between this and `cheapest` is the content of the
    lesson, and because `validate.py` asserts a scenario that claims to teach
    it actually has one.
    """
    return _search(built, lambda e: 1, owned)


def cheapest_through(built, edge, owned=None) -> Path:
    """The cheapest arriving route that is forced through one edge.

    Cost to the edge's source, plus the edge, plus the cheapest route on from
    its destination. Returns unreachable if either leg does not connect. This
    is how a checker asks "is there an arriving route that uses *this* right",
    without the fragile business of deleting edges and hoping the rest of the
    graph still hangs together, which is exactly the bug that made the quiet
    check miss a loud route that shared a tail with the quiet one.
    """
    start = set(owned) if owned is not None else set(built.owned)
    to_src = _search(built, lambda e: cost_of(e.kind), start, target=edge.src)
    if not to_src.reachable:
        return _UNREACHABLE
    have = closure(start | {e.dst for e in to_src.edges} | {edge.dst},
                   built.edges)
    onward = _search(built, lambda e: cost_of(e.kind), have)
    if not onward.reachable:
        return _UNREACHABLE
    edges = tuple(to_src.edges) + (edge,) + tuple(onward.edges)
    return Path(edges=edges, cost=sum(cost_of(x.kind) for x in edges))


def remaining(built, owned) -> Path:
    """The cheapest route from where you have ended up. Shown when a walk runs
    out of budget, and deliberately kept out of the score: getting most of the
    way to Domain Admin is not getting to Domain Admin, exactly as an exploit
    meeting three of four conditions does not work."""
    return cheapest(built, owned)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class WalkScore:
    """The result of one lineage attempt.

    `spent` against `optimal` is the whole score. Everything else on this
    object exists so the debrief can say *why* the walk cost what it did, which
    is the part that teaches.
    """

    reached: bool
    spent: int
    optimal: int
    budget: int
    taken: tuple
    dead_ends: tuple
    left: int = 0            # cheapest remaining cost, when the walk fell short
    elapsed: float = 0.0

    @property
    def total(self) -> float:
        """100 for the cheapest route, halving as you spend double.

        Nothing for a walk that did not arrive, and the partial progress is
        reported separately rather than folded in (see `remaining`).
        """
        if not self.reached or not self.spent:
            return 100.0 if (self.reached and not self.optimal) else 0.0
        return round(min(100.0, 100.0 * self.optimal / self.spent), 1)

    @property
    def band(self) -> str:
        from .scoring import band
        return band(self.total)

    @property
    def overspend(self) -> int:
        return max(0, self.spent - self.optimal)

    def summary(self) -> str:
        if not self.reached:
            return f'ran out at {self.spent} of {self.budget}, {self.left} short'
        if not self.overspend:
            return f'arrived on the cheapest route, {self.spent} spent'
        return f'arrived for {self.spent}, against {self.optimal}'


def score_walk(built, taken, reached: bool, optimal: int, budget: int,
               elapsed: float = 0.0) -> WalkScore:
    """Price a walk. `taken` is the priced rights the student actually used."""
    spent = sum(cost_of(e.kind) for e in taken)
    owned = set(built.owned) | {e.dst for e in taken}
    left = 0
    if not reached:
        rest = remaining(built, owned)
        left = rest.cost if rest.reachable else 0
    return WalkScore(
        reached=reached, spent=spent, optimal=optimal, budget=budget,
        taken=tuple(taken), dead_ends=dead_ends(built, taken),
        left=left, elapsed=elapsed)


def dead_ends(built, taken) -> tuple:
    """Moves that bought a principal with nothing priced leading out of it.

    The graph equivalent of chasing a decoy in `sift`, and worth naming for the
    same reason: everybody knows what they failed to reach, and nobody has ever
    been shown a list of what they paid for that was never going anywhere.

    **The objective is not a dead end**, obviously, and the first version of
    this said it was. The last move of a winning walk buys an account that has
    no priced rights out of it, because it is the end of the road on purpose,
    and "nothing leads out of here" was true of it in exactly the same way it
    is true of a cul-de-sac. A walk that arrived cleanly was therefore told it
    had wasted its winning move. Reaching the objective is checked first.
    """
    out = []
    for e in taken:
        reach = closure({e.dst}, built.edges)
        if built.objective in reach:
            continue
        onward = [x for x in built.edges
                  if x.src in reach and x.kind not in FREE]
        if not onward:
            out.append(e)
    return tuple(out)
