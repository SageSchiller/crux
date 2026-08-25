"""Seeded synthetic Active Directory graphs (crux D10, applied to `lineage`).

**What a lineage fixture is.** A small domain: users, groups, computers and the
rights between them, in the shape a collection tool actually returns. Somewhere
in it is a path from what you hold to what you want, and usually more than one.

**What the seed moves, and what it must never move.** The structure is
authored, because the structure *is* the exercise: which right leads where, and
what each one costs to use, is the thing being taught and it has to be
auditable. What the seed moves is everything a person could memorise instead of
reasoning: the domain name, the display names of the ordinary accounts, the
order every list is printed in, and how many uninteresting principals are
padding the collection out. Nodes keep their **role id** across every seed, so
the answer to "which rights are the path" is stable and `validate.py` can prove
it at eight seeds the same way it does for `sift`.

**Why names are drawn rather than authored, except where they carry meaning.**
A graph where the answer is always `svc_backup` teaches the name. A graph where
every name is drawn teaches nothing at all, because `DOMAIN ADMINS` has to read
as `DOMAIN ADMINS` and a service account has to look like a service account. So
authored names are kept wherever the name is part of the information, and drawn
wherever the account is just a person who happens to be logged in somewhere.

**Nothing here names a real organisation, product or machine** (crux D23). The
domains, the people and the hosts are invented, and the rights are the real
ones, which is the half that transfers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

#: What a principal is. Kept as a small closed set because the display and the
#: sort order both key off it, and a typo'd kind would silently render as a
#: user.
KINDS = ('user', 'group', 'computer', 'domain')


@dataclass(frozen=True, slots=True)
class Node:
    """One principal, identified by the role it plays rather than its name.

    `id` is the authored role (`you`, `svc-backup`, `da`) and never moves with
    the seed. `name` is what the collection displays, and is drawn per seed
    unless the author pinned one.
    """

    id: str
    kind: str
    name: str = ''
    note: str = ''
    #: Computers only: which pool the drawn name comes from. A host the
    #: content calls a database server has to be *named* like one, or the
    #: collection contradicts itself; pinning the name instead would make it
    #: memorable across seeds, which is what crux D10 exists to prevent.
    host: str = 'workstation'
    #: Marks a principal that exists only to make the collection realistic.
    #: Padding is generated rather than authored, so this is set by the
    #: builder rather than in content.
    filler: bool = False

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f'node {self.id!r}: bad kind {self.kind!r}')


@dataclass(frozen=True, slots=True)
class Right:
    """One edge: `src` can do `kind` to `dst`.

    `why` is what taking it actually means on an engagement, and it is what the
    result screen says against the step. Same argument as `Line.why` in `sift`:
    the score tells you that you took an expensive route, and only this tells
    you what made it expensive.
    """

    src: str
    dst: str
    kind: str
    why: str = ''

    @property
    def id(self) -> str:
        """Stable across seeds, because it is built from role ids."""
        return f'{self.src}|{self.kind}|{self.dst}'


@dataclass(frozen=True, slots=True)
class Built:
    """A materialised domain, ready to render and to solve."""

    nodes: tuple[Node, ...]
    edges: tuple[Right, ...]
    owned: tuple[str, ...]
    objective: str
    domain: str
    netbios: str

    def node(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def label(self, node_id: str) -> str:
        n = self.node(node_id)
        return n.name if n else node_id

    def out_of(self, node_id: str) -> tuple[Right, ...]:
        return tuple(e for e in self.edges if e.src == node_id)


# --------------------------------------------------------------------------
# Name pools
# --------------------------------------------------------------------------

_DOMAINS = (
    ('harbord.local', 'HARBORD'),
    ('sentinel.local', 'SENTINEL'),
    ('coldwater.local', 'COLDWATER'),
    ('mirage.internal', 'MIRAGE'),
    ('northgate.lan', 'NORTHGATE'),
    ('ashlow.local', 'ASHLOW'),
)

_FIRST = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n',
          'p', 'r', 's', 't', 'v', 'w')

_LAST = ('mercer', 'okafor', 'delaney', 'novak', 'kirby', 'ashworth',
         'pemberton', 'rutkowski', 'haldane', 'quill', 'marchetti', 'foss',
         'nakamura', 'oyelaran', 'brennan', 'siddiqui', 'varga', 'holloway',
         'castellan', 'ibsen')

_HOST_POOLS = {
    'workstation': ('WKSTN', 'DESK', 'LAP', 'TERM', 'BOOTH'),
    'server': ('SRV-APP', 'SRV-FILE', 'SRV-PRINT', 'SRV-BUILD', 'SRV-MON'),
    'db': ('SQL', 'SQL-PROD', 'DB', 'MSSQL'),
    'dc': ('DC', 'DC-CORE', 'ADDC'),
}

#: Groups that exist in every domain and mean nothing on their own. Used as
#: padding so a collection is not four groups long, and never as a path.
_FILLER_GROUPS = (
    'DOMAIN USERS', 'DOMAIN COMPUTERS', 'PRINT OPERATORS',
    'REMOTE DESKTOP USERS', 'DISTRIBUTED COM USERS', 'CERT PUBLISHERS',
    'DNSADMINS-STAGING', 'ALL STAFF', 'VPN USERS', 'LICENCE READERS',
)


def _rng(seed: int) -> random.Random:
    return random.Random(seed & 0xFFFFFFFF)


def _people(r: random.Random, n: int) -> list[str]:
    """`j.doe`-shaped account names, distinct within one build."""
    out: list[str] = []
    seen: set[str] = set()
    while len(out) < n:
        name = f'{r.choice(_FIRST)}.{r.choice(_LAST)}'
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


# --------------------------------------------------------------------------
# The fixture
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Domain:
    """An authored domain structure that materialises differently per seed.

    `owned` is what you hold at the outset and `objective` is the role id you
    have to end up holding. Both are role ids, so both survive the seed.

    `filler` says how many uninteresting principals to pad the collection with,
    as a range. Padding matters more here than it looks: a domain with nine
    principals in it is a puzzle, and the skill being trained is finding a path
    through a collection where most of what you can see is irrelevant. It is
    the same argument as the noise in a `sift` fixture, and it was measured the
    same way: a graph small enough to read end to end does not train reading a
    graph.
    """

    nodes: tuple[Node, ...]
    edges: tuple[Right, ...]
    owned: tuple[str, ...]
    objective: str
    filler: tuple[int, int] = (10, 16)
    #: Pin the domain instead of drawing one per seed. A standalone collection
    #: leaves this empty and the domain name varies with the seed like every
    #: other surface detail (crux D10). A chain stage sets it, because the
    #: engagement already named the domain in its earlier stages and a graph
    #: that called the same box something different would read as a different
    #: box. The account names, ordering and padding still vary; only the
    #: domain the fiction fixed is fixed.
    domain: str = ''
    netbios: str = ''

    def build(self, seed: int) -> Built:
        r = _rng(seed)
        if self.domain and self.netbios:
            domain, netbios = self.domain, self.netbios
        else:
            domain, netbios = r.choice(_DOMAINS)

        # Draw a name for every node that did not author one. Ordinary people
        # and ordinary workstations are drawn; anything whose name carries
        # information keeps what the author wrote.
        people = _people(r, 40)
        p = iter(people)
        used_hosts: set[str] = set()

        def host_name(pool: str = 'workstation') -> str:
            prefixes = _HOST_POOLS.get(pool, _HOST_POOLS['workstation'])
            while True:
                cand = f'{r.choice(prefixes)}-{r.randint(1, 48):02d}'
                if cand not in used_hosts:
                    used_hosts.add(cand)
                    return cand

        named: list[Node] = []
        for n in self.nodes:
            if n.name:
                name = n.name
            elif n.kind == 'user':
                name = f'{netbios}\\{next(p)}'
            elif n.kind == 'computer':
                name = host_name(n.host)
            elif n.kind == 'domain':
                name = domain.upper()
            else:
                name = f'GROUP-{n.id.upper()}'
            if n.kind == 'user' and not name.startswith(netbios + '\\'):
                name = f'{netbios}\\{name}'
            named.append(Node(id=n.id, kind=n.kind, name=name, note=n.note,
                              host=n.host))

        # Padding. Filler principals carry no edges out and are never on a
        # path; some carry a MemberOf into a filler group so the collection
        # does not read as a list of orphans.
        pad: list[Node] = []
        pad_edges: list[Right] = []
        groups = list(_FILLER_GROUPS)
        r.shuffle(groups)
        n_filler = r.randint(*self.filler)
        for i in range(n_filler):
            if i % 4 == 3:
                gid = f'filler-g{i}'
                pad.append(Node(id=gid, kind='group', name=groups[i % len(groups)],
                                filler=True))
                continue
            if i % 5 == 4:
                cid = f'filler-c{i}'
                pad.append(Node(id=cid, kind='computer', name=host_name(),
                                filler=True))
                continue
            uid = f'filler-u{i}'
            pad.append(Node(id=uid, kind='user',
                            name=f'{netbios}\\{next(p)}', filler=True))

        filler_groups = [n.id for n in pad if n.kind == 'group']
        if filler_groups:
            for n in pad:
                if n.kind == 'user' and r.random() < 0.7:
                    pad_edges.append(Right(n.id, r.choice(filler_groups),
                                           'MemberOf'))

        nodes = named + pad
        edges = list(self.edges) + pad_edges
        # Order is drawn, because a path that is always the third row printed
        # is a path you can find without reading the rights.
        r.shuffle(nodes)
        r.shuffle(edges)
        return Built(nodes=tuple(nodes), edges=tuple(edges),
                     owned=self.owned, objective=self.objective,
                     domain=domain, netbios=netbios)

    def canonical(self) -> Built:
        """The seed-0 build. For `validate.py` and for authoring."""
        return self.build(0)
