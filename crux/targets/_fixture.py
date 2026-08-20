"""Seeded synthetic output builders (crux D10).

**Why fixtures are generated rather than stored.** Three reasons, in the order
they matter.

D2 forbids the obvious source: crux never touches a live host, so output cannot
be captured. The writeups are the next obvious source and are the wrong shape:
they abbreviate a full scan to the three lines that mattered, which is the
opposite of what this track needs, since the whole skill is finding those three
lines among the other forty. And a fixture stored as literal text can be beaten
by remembering that the lead was the fourth line, which trains recall of a
screen rather than the reading of one.

So each attempt draws a fresh seed and rebuilds. The lead keeps its identity
and its meaning; the noise around it, its position, the addresses, the
versions, the counts and the timings all move. **The seed is recorded on the
attempt**, so a run can be reproduced exactly when a key turns out to be wrong,
and `test.py` pins seeds so nothing here is flaky.

**Noise is authentic, not padding.** A real `-sCV` scan is long because of NSE
script output, not because hosts have forty open ports, so that is what these
generate: host keys, titles, server headers, certificate blocks. Padding a
scan with twenty invented open ports would train people to read something that
does not exist.
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field

from ..model import Line

# --------------------------------------------------------------------------
# Shared pieces
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Note:
    """One NSE script line, or any sub-line under an entry."""

    text: str
    kind: str = 'noise'


@dataclass(frozen=True, slots=True)
class Port:
    num: int
    service: str
    version: str = ''
    kind: str = 'noise'
    state: str = 'open'
    scripts: tuple[Note, ...] = ()


@dataclass(frozen=True, slots=True)
class Hit:
    """One web content-discovery result."""

    path: str
    status: int
    size: int = 0
    kind: str = 'noise'
    #: Set to hold the size steady when the size itself is the tell.
    exact: bool = False


@dataclass(frozen=True, slots=True)
class Grant:
    """One sudo rule."""

    text: str
    kind: str = 'noise'


class Fixture:
    """Builds one screen of output from a seed."""

    def build(self, seed: int) -> tuple[Line, ...]:
        raise NotImplementedError

    def canonical(self) -> tuple[Line, ...]:
        """The seed-0 build. Used by `validate.py` and by authoring."""
        return self.build(0)


def _rng(seed: int) -> random.Random:
    return random.Random(seed & 0xFFFFFFFF)


def _slug(prefix: str, text: str, keep: int = 24) -> str:
    """A readable, collision-proof line id derived from the line's content.

    Ids have to come from content rather than position, because entries are
    shuffled and a positional id would move the key with the seed. The
    readable part is truncated so ids stay legible in a report, and truncation
    is exactly what went wrong first: three sudo grants under
    `/usr/local/nagiosxi/scripts/` shared their first forty characters, so
    they shared an id, so marking one marked all three. The checksum is over
    the *whole* text and makes that unrepresentable.

    `zlib.crc32`, not `hash()`: string hashing is salted per process, so ids
    built from it would differ between runs and between `validate.py` and the
    app.
    """
    readable = ''.join(c if c.isalnum() else '-' for c in text).strip('-')
    return f'{prefix}{readable[:keep]}-{zlib.crc32(text.encode()):08x}"'[:-1]


def _host_ip(r: random.Random) -> str:
    """An address that looks like a lab, because every lab address does."""
    return r.choice([
        f'10.10.11.{r.randint(3, 250)}',
        f'10.10.10.{r.randint(3, 250)}',
        f'192.168.{r.randint(50, 200)}.{r.randint(3, 250)}',
        f'172.16.{r.randint(1, 40)}.{r.randint(3, 250)}',
    ])


_NMAP_VERSIONS = ('7.92', '7.93', '7.94', '7.94SVN', '7.95')
_MONTHS = ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12')


def _hexkey(r: random.Random, n: int = 32) -> str:
    return ':'.join(f'{r.randint(0, 255):02x}' for _ in range(n))


# --------------------------------------------------------------------------
# nmap
# --------------------------------------------------------------------------

#: Open ports that are real but tell you nothing on their own. Drawn from to
#: pad a scan out to a believable size and to move the lead's position.
_NOISE_PORTS: tuple[Port, ...] = (
    Port(111, 'rpcbind', '2-4 (RPC #100000)'),
    Port(2049, 'nfs_acl', '3 (RPC #100227)'),
    Port(631, 'ipp', 'CUPS 2.4'),
    Port(25, 'smtp', 'Postfix smtpd'),
    Port(110, 'pop3', 'Dovecot pop3d'),
    Port(143, 'imap', 'Dovecot imapd'),
    Port(953, 'rndc', ''),
    Port(5355, 'llmnr', ''),
    Port(8009, 'ajp13', 'Apache Jserv (Protocol v1.3)'),
    Port(9000, 'cslistener', ''),
    Port(10000, 'snet-sensor-mgmt', ''),
    Port(32768, 'filenet-tms', ''),
)


class NmapScan(Fixture):
    """A TCP scan, with or without version detection.

    `version_scan=False` renders the SERVICE column from nmap's port-number
    table and no VERSION column, which is what a bare `-p-` sweep actually
    prints. That distinction carries a whole lesson: a service *name* in that
    column is a guess from a lookup table, not an identification, and treating
    it as fact is how people walk past a database on a strange port.
    """

    def __init__(self, ports: tuple[Port, ...], noise: tuple[int, int] = (0, 0),
                 version_scan: bool = True, os_line: str = '',
                 host: str = '', closed: tuple[int, int] = (65520, 65533)) -> None:
        self.ports = ports
        self.noise = noise
        self.version_scan = version_scan
        self.os_line = os_line
        self.host = host
        self.closed = closed

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        target = self.host or _host_ip(r)

        n_noise = r.randint(*self.noise) if self.noise[1] else 0
        taken = {p.num for p in self.ports}
        pool = [p for p in _NOISE_PORTS if p.num not in taken]
        r.shuffle(pool)
        ports = sorted(list(self.ports) + pool[:n_noise], key=lambda p: p.num)

        out: list[Line] = []
        add = lambda i, t, k='noise': out.append(Line(i, t, k))

        ver = r.choice(_NMAP_VERSIONS)
        date = f'2026-{r.choice(_MONTHS)}-{r.randint(10, 28)} {r.randint(9, 22):02d}:{r.randint(0, 59):02d}'
        add('h1', f'Starting Nmap {ver} ( https://nmap.org ) at {date} BST')
        add('h2', f'Nmap scan report for {target}')
        add('h3', f'Host is up (0.0{r.randint(11, 89)}s latency).')
        add('h4', f'Not shown: {r.randint(*self.closed)} closed tcp ports (reset)')
        if self.version_scan:
            add('h5', 'PORT      STATE    SERVICE       VERSION')
        else:
            add('h5', 'PORT      STATE    SERVICE')

        for p in ports:
            # 14, not 13: `ms-wbt-server` is exactly 13 characters and ran
            # straight into the version column with no space between them.
            head = f'{p.num}/tcp'.ljust(10) + p.state.ljust(9) + p.service.ljust(14)
            if self.version_scan and p.version:
                head += p.version
            add(f'p{p.num}', head.rstrip(), p.kind)
            if not self.version_scan:
                continue
            for j, note in enumerate(self._scripts_for(p, r)):
                add(f'p{p.num}s{j}', note.text, note.kind)

        if self.os_line:
            add('t0', self.os_line)
        add('t1', '')
        add('t2', 'Service detection performed. Please report any incorrect '
                  'results at https://nmap.org/submit/ .')
        add('t3', f'Nmap done: 1 IP address (1 host up) scanned in '
                  f'{r.randint(18, 240)}.{r.randint(10, 99)} seconds')
        return tuple(out)

    def _scripts_for(self, p: Port, r: random.Random) -> list[Note]:
        """Authored script lines, plus the generic ones nmap emits anyway."""
        notes = list(p.scripts)
        if p.scripts or not p.version:
            return notes
        if p.service == 'ssh':
            notes.append(Note('| ssh-hostkey:'))
            for bits, algo in ((3072, 'RSA'), (256, 'ECDSA'), (256, 'ED25519')):
                notes.append(Note(f'|   {bits} {_hexkey(r, 16)} ({algo})'))
        elif p.service in ('http', 'https'):
            notes.append(Note(f'|_http-server-header: {p.version}'))
        return notes


# --------------------------------------------------------------------------
# web content discovery
# --------------------------------------------------------------------------

#: Paths a wordlist finds on nearly every host. Present so that a real find has
#: something to hide among, which is the whole difficulty of reading these.
_NOISE_PATHS: tuple[tuple[str, int], ...] = (
    ('/images', 301), ('/css', 301), ('/js', 301), ('/assets', 301),
    ('/fonts', 301), ('/vendor', 301), ('/static', 301), ('/media', 301),
    ('/icons', 403), ('/server-status', 403), ('/server-info', 403),
    ('/cgi-bin', 403), ('/.htaccess', 403), ('/.htpasswd', 403),
    ('/index.html', 200), ('/index.php', 200), ('/about', 200),
    ('/contact', 200), ('/login', 200), ('/robots.txt', 200),
    ('/favicon.ico', 200), ('/style.css', 200), ('/LICENSE', 200),
)


class FeroxRun(Fixture):
    """A `feroxbuster` run. Results arrive as found, so order genuinely varies.

    Sizes are generated per path and kept stable within one build, because the
    tell in this output is very often a size that does not match its
    neighbours, and a size that reshuffled between the header and the body
    would make that unreadable.
    """

    def __init__(self, host: str, hits: tuple[Hit, ...],
                 noise: tuple[int, int] = (14, 22), scheme: str = 'http',
                 wildcard_size: int = 0) -> None:
        self.host = host
        self.hits = hits
        self.noise = noise
        self.scheme = scheme
        #: When set, every 200 in the run comes back at exactly this length,
        #: which is what a catch-all route or a soft 404 actually looks like.
        #: Without it the noise sizes scatter and the "every row is the same
        #: number" scenario has no same number in it.
        self.wildcard_size = wildcard_size

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        base = f'{self.scheme}://{self.host}'
        n_noise = r.randint(*self.noise)
        taken = {h.path for h in self.hits}
        pool = [p for p in _NOISE_PATHS if p[0] not in taken]
        r.shuffle(pool)
        noise = [Hit(path, status, 0) for path, status in pool[:n_noise]]

        rows = list(self.hits) + noise
        r.shuffle(rows)

        # Pages cut from one template come back at similar lengths, so the
        # noise 200s cluster and an authored size can sit visibly outside the
        # cluster. Drawing every 200 from a wide range instead, which is what
        # this did first, meant a "size anomaly" scenario contained no
        # anomaly: the lead was just another number in a column of noise.
        base_200 = self.wildcard_size or r.randint(3200, 6200)

        out: list[Line] = []
        out.append(Line('h1', ' ' + '_' * 62))
        out.append(Line('h2', f' Target Url            {base}'))
        out.append(Line('h3', ' Wordlist              raft-medium-directories.txt'))
        out.append(Line('h4', f' Threads               {r.choice((30, 50, 50, 100))}'))
        out.append(Line('h5', ' Status Codes          All Status Codes!'))
        out.append(Line('h6', ' ' + '_' * 62))

        for h in rows:
            size = self._size(r, h, base_200)
            if self.wildcard_size and size == self.wildcard_size:
                # One page answering to every name is byte-identical, so its
                # line and word counts have to match too. Jittering them made
                # the rows look merely similar, which is the one thing this
                # scenario must not look like.
                lines_n, words = max(1, size // 40), max(1, size // 11)
            else:
                lines_n = max(1, size // r.randint(28, 48))
                words = max(1, size // r.randint(6, 12))
            path = h.path
            arrow = f' => {base}{path}/' if h.status in (301, 302) else ''
            text = (f'{h.status:<8} GET {lines_n:>8}l {words:>8}w {size:>8}c '
                    f'{base}{path}{arrow}')
            out.append(Line(_slug('f', path), text, h.kind))

        out.append(Line('t1', ''))
        out.append(Line('t2', f'[####################] - {r.randint(20, 90)}s '
                              f'{r.randint(29000, 30000)}/{r.randint(29000, 30000)} '
                              f'{r.randint(300, 900)}/s'))
        return tuple(out)

    def _size(self, r: random.Random, h: Hit, base_200: int) -> int:
        if h.exact and h.size:
            return h.size
        if h.status in (301, 302):
            return r.randint(300, 340)
        if h.status == 403:
            return r.randint(270, 290)
        if self.wildcard_size:
            return self.wildcard_size
        return base_200 + r.randint(-380, 380)


# --------------------------------------------------------------------------
# sudo -l
# --------------------------------------------------------------------------

_DEFAULTS = (
    'env_reset', 'mail_badpass', 'use_pty', 'insults', 'lecture=once',
    'timestamp_timeout=15', 'passwd_tries=3', 'listpw=any',
)


class SudoL(Fixture):
    """`sudo -l` output.

    Grant order is shuffled, because sudoers order is an authoring accident on
    the target rather than a signal, and a student who learns "the exploitable
    one is last" has learned nothing about sudo.
    """

    def __init__(self, user: str, host: str, grants: tuple[Grant, ...],
                 needs_password: bool = False) -> None:
        self.user = user
        self.host = host
        self.grants = grants
        self.needs_password = needs_password

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        out: list[Line] = []
        if self.needs_password:
            out.append(Line('h0', f'[sudo] password for {self.user}:'))
        out.append(Line('h1', f'Matching Defaults entries for {self.user} on '
                              f'{self.host}:'))
        picked = list(_DEFAULTS[:2]) + r.sample(_DEFAULTS[2:], r.randint(2, 4))
        out.append(Line('h2', '    ' + ', '.join(picked) + ','))
        out.append(Line('h3', '    secure_path=/usr/local/sbin\\:/usr/local/bin'
                              '\\:/usr/sbin\\:/usr/bin\\:/sbin\\:/bin'))
        out.append(Line('h4', ''))
        out.append(Line('h5', f'User {self.user} may run the following commands '
                              f'on {self.host}:'))

        grants = list(self.grants)
        r.shuffle(grants)
        for g in grants:
            out.append(Line(_slug('g', g.text), '    ' + g.text, g.kind))
        return tuple(out)
