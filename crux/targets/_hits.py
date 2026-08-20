"""What arrived at a mock target, and whether it was the right thing.

**The design decision this module exists to express.** A salvage scenario
could be scored as a boolean: the exploit landed or it did not. That is
honest, verifiable, and almost useless as teaching, because a proof-of-concept
that does not work fails silently and the whole difficulty is finding out
*which* of six things is wrong with it.

So the target records every request and scores it against a list of
single-purpose requirements. When nothing lands, crux reports the request that
came **closest** and names the first requirement it missed. That turns "it did
not work" into "your request reached the right endpoint with the right method
and the payload arrived URL-encoded once when the parameter is decoded twice",
which is the sentence a person actually needs.

Requirements check one thing each, deliberately. A requirement that checked
method and path together could only ever say "the request line was wrong".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, unquote, urlsplit


@dataclass(frozen=True, slots=True)
class Request:
    """One thing that arrived at a mock target."""

    method: str
    target: str                      # path plus query, as sent
    headers: tuple[tuple[str, str], ...] = ()
    body: bytes = b''
    raw: bytes = b''                 # for the TCP target, the whole payload

    @property
    def route(self) -> str:
        return urlsplit(self.target).path

    @property
    def query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.target).query, keep_blank_values=True)

    def header(self, name: str) -> str:
        low = name.lower()
        for k, v in self.headers:
            if k.lower() == low:
                return v
        return ''

    @property
    def form(self) -> dict[str, list[str]]:
        try:
            return parse_qs(self.body.decode('utf-8', 'replace'),
                            keep_blank_values=True)
        except ValueError:
            return {}

    def text(self) -> str:
        return self.body.decode('utf-8', 'replace')


#: The kinds of check a requirement can be. One per requirement, so that the
#: feedback can name exactly one thing.
KINDS = ('method', 'route', 'header', 'query', 'form', 'body', 'body_absent',
         'raw')


@dataclass(frozen=True, slots=True)
class Requirement:
    """One condition a correct request has to satisfy.

    `hint` is what the student is told when this is the first unmet condition
    on their closest attempt. It should describe the gap, not the answer: the
    point is to send them back to the script knowing where to look.
    """

    name: str
    kind: str
    value: str
    hint: str = ''
    key: str = ''                    # header name, query key, or form field

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f'requirement {self.name!r}: bad kind {self.kind!r}')
        if self.kind in ('header', 'query', 'form') and not self.key:
            raise ValueError(f'requirement {self.name!r}: {self.kind} needs a key')

    def met_by(self, r: Request) -> bool:
        k = self.kind
        if k == 'method':
            return r.method.upper() == self.value.upper()
        if k == 'route':
            return r.route == self.value
        if k == 'header':
            return self.value.lower() in r.header(self.key).lower()
        if k == 'query':
            return any(self.value in v for v in r.query.get(self.key, ()))
        if k == 'form':
            return any(self.value in v for v in r.form.get(self.key, ()))
        if k == 'body':
            return self.value in r.text()
        if k == 'body_absent':
            # For encoding defects: the payload must arrive *decoded*, so the
            # still-encoded form must be absent. Checking only for the decoded
            # form would pass on a double-encoded value that happens to
            # contain it.
            return self.value not in r.text()
        return self.value.encode() in r.raw


@dataclass
class HitRecord:
    """Everything that arrived, and the verdict over it.

    Shared by both mock targets so a scenario can move between HTTP and raw
    TCP without the screen or the scoring knowing which it is talking to.
    """

    requirements: tuple[Requirement, ...]
    requests: list[Request] = field(default_factory=list)

    def record(self, r: Request) -> None:
        self.requests.append(r)

    @property
    def count(self) -> int:
        return len(self.requests)

    def met(self, r: Request) -> tuple[Requirement, ...]:
        return tuple(q for q in self.requirements if q.met_by(r))

    def landed(self) -> bool:
        return any(len(self.met(r)) == len(self.requirements)
                   for r in self.requests)

    def closest(self) -> Request | None:
        """The request that satisfied the most conditions.

        Ties go to the most recent, because the most recent is the one the
        student just changed something to produce.
        """
        best, best_n = None, -1
        for r in self.requests:
            n = len(self.met(r))
            if n >= best_n:
                best, best_n = r, n
        return best

    def first_unmet(self, r: Request) -> Requirement | None:
        for q in self.requirements:
            if not q.met_by(r):
                return q
        return None

    def verdict(self) -> tuple[bool, str, int]:
        """(landed, one sentence, how many conditions the best attempt met)."""
        if not self.requests:
            return False, 'Nothing reached the target at all.', 0
        if self.landed():
            return True, 'The exploit landed.', len(self.requirements)
        best = self.closest()
        n = len(self.met(best))
        missed = self.first_unmet(best)
        detail = missed.hint or f'{missed.name} was wrong' if missed else 'unknown'
        return False, detail, n
