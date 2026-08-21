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
    why: str = ''


@dataclass(frozen=True, slots=True)
class Port:
    num: int
    service: str
    version: str = ''
    kind: str = 'noise'
    why: str = ''
    state: str = 'open'
    scripts: tuple[Note, ...] = ()


@dataclass(frozen=True, slots=True)
class Hit:
    """One web content-discovery result."""

    path: str
    status: int
    size: int = 0
    kind: str = 'noise'
    why: str = ''
    #: Set to hold the size steady when the size itself is the tell.
    exact: bool = False


@dataclass(frozen=True, slots=True)
class Grant:
    """One sudo rule."""

    text: str
    kind: str = 'noise'
    why: str = ''


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
        add = lambda i, t, k='noise', w='': out.append(Line(i, t, k, w))

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
            add(f'p{p.num}', head.rstrip(), p.kind, p.why)
            if not self.version_scan:
                continue
            for j, note in enumerate(self._scripts_for(p, r)):
                add(f'p{p.num}s{j}', note.text, note.kind, note.why)

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
            out.append(Line(_slug('f', path), text, h.kind, h.why))

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
            out.append(Line(_slug('g', g.text), '    ' + g.text, g.kind, g.why))
        return tuple(out)


# --------------------------------------------------------------------------
# SMB share enumeration
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Share:
    name: str
    type: str = 'Disk'
    comment: str = ''
    perms: str = ''
    kind: str = 'noise'
    why: str = ''


#: Present on essentially every Windows host. A scenario that did not include
#: them would be teaching people to read a screen they will never see.
_DEFAULT_SHARES = (
    Share('ADMIN$', 'Disk', 'Remote Admin'),
    Share('C$', 'Disk', 'Default share'),
    Share('IPC$', 'IPC', 'Remote IPC'),
    Share('print$', 'Disk', 'Printer Drivers'),
)


class SmbShares(Fixture):
    """Share enumeration, in one of two real output shapes.

    `style='nxc'` reproduces `nxc smb --shares`, whose every row is prefixed
    with protocol, address, port and NetBIOS name. That prefix costs about
    fifty columns before any content starts, which is authentic and is also
    why it is not the default: a screen where **every** line needs panning is
    a screen nobody reads. It is the right choice only when the tell is in the
    banner, where the domain name, the build and the signing state live.

    `style='smbclient'` reproduces `smbclient -L`, which is compact and is
    what a share name has to stand out against most of the time.
    """

    def __init__(self, host: str, netbios: str, domain: str,
                 shares: tuple[Share, ...], user: str = 'guest',
                 signing: bool = True, os_name: str = 'Windows Server 2022 '
                                                      'Build 20348 x64',
                 include_defaults: bool = True,
                 style: str = 'smbclient', banner_why: str = '') -> None:
        self.style = style
        #: Why the banner is the finding, when `signing=False` makes it one.
        self.banner_why = banner_why
        self.host = host
        self.netbios = netbios
        self.domain = domain
        self.shares = shares
        self.user = user
        self.signing = signing
        self.os_name = os_name
        self.include_defaults = include_defaults

    def _all_shares(self, r: random.Random) -> list[Share]:
        shares = list(self.shares)
        if self.include_defaults:
            taken = {sh.name for sh in shares}
            shares += [sh for sh in _DEFAULT_SHARES if sh.name not in taken]
        r.shuffle(shares)
        # Real listings put the administrative `$` shares together, so the
        # interesting one does not get to stand out merely by being adjacent
        # to nothing.
        shares.sort(key=lambda sh: sh.name.endswith('$'))
        return shares

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        ip = self.host or _host_ip(r)
        shares = self._all_shares(r)
        out: list[Line] = []

        if self.style == 'nxc':
            pre = f'SMB   {ip:<15} 445  {self.netbios:<10} '
            out.append(Line('h1', pre + f'[*] {self.os_name} '
                                        f'(domain:{self.domain}) '
                                        f'(signing:{self.signing}) '
                                        f'(SMBv1:False)',
                            'lead' if not self.signing else 'noise',
                            self.banner_why if not self.signing else ''))
            out.append(Line('h2', pre + f'[+] {self.domain}\\{self.user}: '))
            out.append(Line('h3', pre + '[*] Enumerated shares'))
            out.append(Line('h4', pre + 'Share        Permissions  Remark'))
            out.append(Line('h5', pre + '-----        -----------  ------'))
            for sh in shares:
                out.append(Line(_slug('s', sh.name),
                                pre + f'{sh.name:<12} {sh.perms:<12} '
                                      f'{sh.comment}',
                                sh.kind, sh.why))
            return tuple(out)

        out.append(Line('h1', f'Anonymous login successful'))
        out.append(Line('h2', ''))
        out.append(Line('h3', '        Sharename       Type      Comment'))
        out.append(Line('h4', '        ---------       ----      -------'))
        for sh in shares:
            row = f'        {sh.name:<15} {sh.type:<9} {sh.comment}'
            if sh.perms:
                row += f'  [{sh.perms}]'
            out.append(Line(_slug('s', sh.name), row.rstrip(), sh.kind, sh.why))
        out.append(Line('t1', ''))
        out.append(Line('t2', 'Reconnecting with SMB1 for workgroup listing.'))
        out.append(Line('t3', 'do_connect: Connection to '
                              f'{ip} failed (Error NT_STATUS_RESOURCE_'
                              'NAME_NOT_FOUND)'))
        out.append(Line('t4', 'Unable to connect with SMB1 -- no workgroup '
                              'available'))
        return tuple(out)


# --------------------------------------------------------------------------
# Local enumeration output (linpeas-shaped)
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Section:
    """One titled block of enumeration output."""

    title: str
    rows: tuple[Note, ...]


class PeasChunk(Fixture):
    """A slice of a local enumeration script's output.

    **ASCII only, deliberately.** The real tool draws its section headers with
    box-drawing characters, and reproducing them would put non-ASCII into
    content that has to survive the ASCII rung on a terminal that cannot
    render it. The substance being drilled is the file list, not the border,
    and the tool degrades to ASCII on such a terminal anyway.

    Section order is shuffled; row order inside a section is not, because a
    directory listing has an order and scrambling it would look wrong to
    anyone who has read one.
    """

    def __init__(self, sections: tuple[Section, ...], user: str = 'www-data',
                 shuffle_sections: bool = True) -> None:
        self.sections = sections
        self.user = user
        self.shuffle_sections = shuffle_sections

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        sections = list(self.sections)
        if self.shuffle_sections:
            r.shuffle(sections)

        out: list[Line] = []
        for i, sec in enumerate(sections):
            out.append(Line(f'sec{i}', ''))
            out.append(Line(_slug('h', sec.title),
                            f'====( {sec.title} )' + '=' * max(
                                0, 56 - len(sec.title))))
            for row in sec.rows:
                out.append(Line(_slug('r', row.text), row.text, row.kind, row.why))
        return tuple(out)


# --------------------------------------------------------------------------
# Listening sockets
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Socket:
    proto: str
    local: str
    state: str = 'LISTEN'
    program: str = '-'
    kind: str = 'noise'
    why: str = ''
    foreign: str = '0.0.0.0:*'


#: Sockets a stock Linux server is listening on before anybody deploys
#: anything. Real `netstat -tulpn` on a server is fifteen to twenty rows, not
#: six, and the scoring profile is what showed that the fixtures were short:
#: on a nine-line screen, marking everything scored 31 rather than the 5 it
#: scores on a realistic one. A screen too small to be wrong on is a screen
#: that cannot teach restraint.
_NOISE_SOCKETS: tuple[Socket, ...] = (
    Socket('tcp', '0.0.0.0:111', program='1/systemd'),
    Socket('tcp', '0.0.0.0:25', program='1044/master'),
    Socket('tcp', '127.0.0.1:25', program='1044/master'),
    Socket('tcp', '0.0.0.0:631', program='702/cupsd'),
    Socket('tcp6', ':::22', program='-'),
    Socket('tcp6', ':::111', program='1/systemd'),
    Socket('udp', '0.0.0.0:111', state='', program='1/systemd'),
    Socket('udp', '0.0.0.0:631', state='', program='702/cups-browsed'),
    Socket('udp', '0.0.0.0:5353', state='', program='688/avahi-daemon'),
    Socket('udp6', ':::5353', state='', program='688/avahi-daemon'),
)


class NetstatDump(Fixture):
    """`netstat -tulpn` output, sorted the way netstat sorts it."""

    def __init__(self, sockets: tuple[Socket, ...],
                 header: str = 'Active Internet connections (only servers)',
                 noise: tuple[int, int] = (5, 8)) -> None:
        self.sockets = sockets
        self.header = header
        self.noise = noise

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        out = [
            Line('h1', self.header),
            Line('h2', 'Proto Recv-Q Send-Q Local Address           '
                       'Foreign Address         State       PID/Program name'),
        ]
        taken = {(s.proto, s.local) for s in self.sockets}
        pool = [s for s in _NOISE_SOCKETS if (s.proto, s.local) not in taken]
        r.shuffle(pool)
        rows = list(self.sockets) + pool[:r.randint(*self.noise)]
        rows.sort(key=lambda s: (s.proto, s.local.rsplit(':', 1)[-1].zfill(6)))
        for s in rows:
            out.append(Line(
                _slug('n', f'{s.proto}{s.local}'),
                f'{s.proto:<5} {0:>6} {0:>6} {s.local:<23} {s.foreign:<23} '
                f'{s.state:<11} {s.program}',
                s.kind, s.why))
        return tuple(out)


# --------------------------------------------------------------------------
# Directory user objects
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DirUser:
    name: str
    description: str = ''
    kind: str = 'noise'
    why: str = ''
    flags: str = ''


class LdapUsers(Fixture):
    """A directory user dump, one attribute block per account.

    The classic finding here is a password in a `description`, so the noise
    accounts carry the kind of descriptions real directories actually contain:
    ticket numbers, owners, dates, and nothing.
    """

    _FILLER = (
        'Managed by IT', 'Created by migration 2019', 'Do not delete',
        'Service account', 'Owner: helpdesk', 'REQ-40114',
        'Temporary account', '', '', 'Contractor - review annually',
    )

    def __init__(self, domain: str, users: tuple[DirUser, ...],
                 noise: tuple[int, int] = (5, 9)) -> None:
        self.domain = domain
        self.users = users
        self.noise = noise

    _NAMES = ('jbrown', 'asmith', 'mpatel', 'rgarcia', 'lnguyen', 'kwilson',
              'dkim', 'tmurphy', 'svc_iis', 'svc_sql', 'backupsvc', 'helpdesk')

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        taken = {u.name for u in self.users}
        pool = [n for n in self._NAMES if n not in taken]
        r.shuffle(pool)
        extra = [DirUser(n, r.choice(self._FILLER))
                 for n in pool[:r.randint(*self.noise)]]
        users = list(self.users) + extra
        r.shuffle(users)

        out = [Line('h1', f'# extended LDIF for {self.domain}'), Line('h2', '')]
        for u in users:
            out.append(Line(_slug('u', u.name), f'sAMAccountName: {u.name}'))
            out.append(Line(_slug('d', u.name + u.description),
                            f'description: {u.description}', u.kind, u.why))
            if u.flags:
                out.append(Line(_slug('f', u.name), f'userAccountControl: {u.flags}',
                                u.kind if not u.description else 'noise',
                                u.why if not u.description else ''))
            out.append(Line(_slug('b', u.name), ''))
        return tuple(out)


# --------------------------------------------------------------------------
# An HTTP response
# --------------------------------------------------------------------------

class HttpResponse(Fixture):
    """Response headers followed by page source.

    Header order is shuffled below the status line, because servers and
    proxies genuinely reorder them and a student who learns "the interesting
    header is fourth" has learned the fixture rather than the protocol.
    """

    _FILLER = (
        'Connection: close', 'Accept-Ranges: bytes', 'Vary: Accept-Encoding',
        'Cache-Control: no-store, no-cache, must-revalidate',
        'Pragma: no-cache', 'Content-Type: text/html; charset=UTF-8',
        'Transfer-Encoding: chunked', 'Expires: Thu, 19 Nov 1981 08:52:00 GMT',
    )

    def __init__(self, status: str, headers: tuple[Note, ...],
                 source: tuple[Note, ...] = (), noise: tuple[int, int] = (3, 5),
                 host: str = '') -> None:
        self.status = status
        self.headers = headers
        self.source = source
        self.noise = noise
        self.host = host

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        out = [Line('h0', self.status)]
        rows = list(self.headers)
        pool = [f for f in self._FILLER
                if not any(f.split(':')[0] == h.text.split(':')[0]
                           for h in self.headers)]
        r.shuffle(pool)
        rows += [Note(f) for f in pool[:r.randint(*self.noise)]]
        rows.append(Note(f'Date: Wed, {r.randint(10, 28)} Aug 2026 '
                         f'{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:00 GMT'))
        r.shuffle(rows)
        for h in rows:
            out.append(Line(_slug('h', h.text), h.text, h.kind, h.why))
        if self.source:
            out.append(Line('sep', ''))
            for src in self.source:
                out.append(Line(_slug('s', src.text), src.text, src.kind, src.why))
        return tuple(out)


# --------------------------------------------------------------------------
# Windows: whoami /priv
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Priv:
    name: str
    desc: str
    state: str = 'Enabled'
    kind: str = 'noise'
    why: str = ''


#: Privileges that grant nothing on their own and turn up on ordinary and
#: service accounts alike. Present so the one privilege that matters has the
#: furniture to hide among, which is the entire reading problem on this
#: screen. A real token lists eight to a dozen of these and which ones depends
#: on the account, so a seeded subset is both the honest rendering and what
#: keeps the screen from being memorable by row position (crux D10).
_STOCK_PRIVS: tuple[Priv, ...] = (
    Priv('SeIncreaseWorkingSetPrivilege', 'Increase a process working set',
         'Disabled'),
    Priv('SeShutdownPrivilege', 'Shut down the system', 'Disabled'),
    Priv('SeUndockPrivilege', 'Remove computer from docking station',
         'Disabled'),
    Priv('SeTimeZonePrivilege', 'Change the time zone', 'Disabled'),
    Priv('SeSystemtimePrivilege', 'Change the system time', 'Disabled'),
    Priv('SeProfileSingleProcessPrivilege', 'Profile single process',
         'Disabled'),
    Priv('SeIncreaseBasePriorityPrivilege',
         'Increase scheduling priority', 'Disabled'),
    Priv('SeCreatePagefilePrivilege', 'Create a pagefile', 'Disabled'),
    Priv('SeManageVolumePrivilege', 'Perform volume maintenance tasks',
         'Disabled'),
)

#: Held by literally every account, and always listed first because of the
#: order the token is built in. Kept out of the drawn pool so it is always
#: present and always at the top, which is what real output looks like.
_ALWAYS_PRIV = Priv('SeChangeNotifyPrivilege', 'Bypass traverse checking')


class WhoamiPriv(Fixture):
    """`whoami /priv` output, in the real column layout.

    Service accounts carry a handful of privileges that every account has and,
    occasionally, one that hands you the machine. The columns are wide and the
    names all begin `Se`, which is exactly why the interesting row is so easy
    to scroll past.
    """

    def __init__(self, user: str, privs: tuple[Priv, ...],
                 stock: tuple[int, int] = (5, 8)) -> None:
        self.user = user
        self.privs = privs
        self.stock = stock

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        rows = list(self.privs)
        taken = {p.name for p in rows}
        pool = [p for p in _STOCK_PRIVS if p.name not in taken]
        if self.stock[1]:
            n = min(r.randint(*self.stock), len(pool))
            rows += r.sample(pool, n)
        r.shuffle(rows)
        # `SeChangeNotify` is on every account and always listed first,
        # because of the order the token is built in. Everything after it is
        # genuinely unordered.
        if _ALWAYS_PRIV.name not in taken:
            rows.insert(0, _ALWAYS_PRIV)
        else:
            rows.sort(key=lambda p: p.name != _ALWAYS_PRIV.name)

        out: list[Line] = [
            Line('h1', f'{self.user}'),
            Line('h2', ''),
            Line('h3', 'PRIVILEGES INFORMATION'),
            Line('h4', '----------------------'),
            Line('h5', ''),
            Line('h6', 'Privilege Name                Description'
                       '                                    State'),
            Line('h7', '============================= '
                       '========================================== ========'),
        ]
        for p in rows:
            out.append(Line(_slug('p', p.name),
                            f'{p.name:<29} {p.desc:<42} {p.state}', p.kind, p.why))
        return tuple(out)


# --------------------------------------------------------------------------
# A plain block of command output
# --------------------------------------------------------------------------

class TextBlock(Fixture):
    """Straight command output: a fixed header, then rows that may shuffle.

    For the screens whose shape is neither a table nor a scan: an `icacls`
    listing, a `sc qc`, a directory. Rows carry their own kind, so a lead is
    authored exactly as it is everywhere else.
    """

    def __init__(self, header: tuple[str, ...], rows: tuple[Note, ...],
                 shuffle: bool = False, footer: tuple[str, ...] = (),
                 noise_pool: tuple[Note, ...] = (),
                 noise: tuple[int, int] = (0, 0)) -> None:
        self.header = header
        self.rows = rows
        #: Real ACL listings do not fix their order, so shuffling is honest
        #: there. Command output with named fields (`sc qc`) does fix it, and
        #: shuffling that would look wrong to anyone who has read one.
        self.shuffle = shuffle
        self.footer = footer
        #: Extra rows this command really does print, drawn per seed and kept
        #: in pool order so the field sequence still looks like the tool. This
        #: is what varies the screen between attempts (crux D10) for output
        #: whose rows cannot be reordered. Authored rows, and therefore every
        #: lead, keep their text and so keep their ids.
        self.noise_pool = noise_pool
        self.noise = noise

    def build(self, seed: int) -> tuple[Line, ...]:
        r = _rng(seed)
        out: list[Line] = [Line(f'h{i}', h) for i, h in enumerate(self.header)]
        rows = list(self.rows)
        if self.noise_pool and self.noise[1]:
            take = r.randint(*self.noise)
            picked = sorted(r.sample(range(len(self.noise_pool)),
                                     min(take, len(self.noise_pool))))
            extra = [self.noise_pool[i] for i in picked]
            # Interleave at seeded positions, keeping pool order intact.
            for note in extra:
                rows.insert(r.randint(0, len(rows)), note)
        if self.shuffle:
            r.shuffle(rows)
        for row in rows:
            out.append(Line(_slug('r', row.text), row.text, row.kind, row.why))
        out += [Line(f't{i}', t) for i, t in enumerate(self.footer)]
        return tuple(out)
