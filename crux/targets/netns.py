"""Real network topologies out of unprivileged namespaces (crux D13).

**Both halves of conduit live here.** `Topology` is the host side: it
describes a network, checks whether this machine can build one, and runs an
attempt. `main()` is the namespace side, invoked as
`unshare -Urnm --map-auto python3 -m crux.targets.netns`, which actually
builds it. They talk over one JSON spec on stdin and one JSON result on
stdout, and nothing else.

**Why one shot rather than a long-lived supervisor.** The first design held
the namespaces open for the life of the scenario and handed the student an
interactive shell inside the attacker namespace. It is more realistic and it
is a great deal more machinery: a control protocol, terminal hand-off of the
real tty to a process inside a user namespace, and a supervisor whose death
has to be survivable at every point. The build takes about two seconds, so
instead each attempt builds the whole network, runs your tunnel script inside
the attacker namespace, probes, reports, and exits. Teardown stops being a
problem to solve and becomes a consequence of the process ending.

It also makes the exercise the same shape as `salvage`: edit a file, run it,
be told exactly what did and did not happen.

**What was learned making this work**, all of it non-obvious and all of it
load-bearing:

* `unshare -Urn` alone is not enough for `sshd`. Its privilege separation
  needs to `setuid` to a user that must exist *inside* the namespace, so the
  map has to cover more than uid 0. `--map-auto` uses the `/etc/subuid` range
  and gives the whole 65536.
* `sshd` refuses to start unless its privsep directory is owned by root, and
  the real one belongs to real root, which reads as `nobody` inside. A bind
  mount of a directory we own fixes it, which is why a mount namespace is in
  the flags.
* The host account is irrelevant and must be: sshd read the real
  `/etc/shadow` and refused because root is locked there. crux supplies its
  own `passwd`, `group` and `shadow` over bind mounts, so a scenario behaves
  the same for every user on every machine.
* `authorized_keys` is read as the logging-in uid, which cannot traverse a
  `0700` directory owned by someone else. The pivot home is a tmpfs inside
  the namespace, which also makes it look like a real home.
* `lo` starts down in a fresh namespace, and a forward to `127.0.0.1` fails
  with "network is unreachable" until it is up.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ATTACKER = 'attacker'
SSH_PORT = 2222
BUILD_TIMEOUT = 90


# --------------------------------------------------------------------------
# Description
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Link:
    """A point-to-point subnet between two hosts. `a` gets .1, `b` gets .2."""

    a: str
    b: str
    net: str                      # e.g. '10.9.0'

    def addr(self, host: str) -> str:
        return f'{self.net}.1' if host == self.a else f'{self.net}.2'


@dataclass(frozen=True, slots=True)
class Service:
    """A listener crux runs inside a namespace, answering with a flag."""

    host: str
    addr: str
    port: int
    flag: str


@dataclass(frozen=True, slots=True)
class Probe:
    """What must be reachable from where for the attempt to have worked.

    `socks` makes the probe go through a SOCKS5 proxy instead of connecting
    directly, which is the only way to verify a dynamic forward. It is spoken
    in twenty lines of stdlib rather than shelled out to `proxychains`,
    because what has to be proved is that **the proxy works**, and borrowing a
    third-party client to prove it would add a dependency and a second thing
    that can be at fault.
    """

    frm: str
    addr: str
    port: int
    expect: str
    name: str = ''
    socks: tuple[str, int] | None = None


@dataclass(frozen=True, slots=True)
class Topology:
    hosts: tuple[str, ...]
    links: tuple[Link, ...]
    services: tuple[Service, ...] = ()
    sshd_on: tuple[str, ...] = ()
    #: Extra `sshd_config` lines for this topology only. Exists so a scenario
    #: can turn forwarding off, which is a real thing to run into and cannot
    #: be taught with a config every scenario shares.
    sshd_extra: tuple[str, ...] = ()
    routes: tuple[tuple[str, str, str], ...] = ()   # (host, dest, via)
    probes: tuple[Probe, ...] = ()
    #: Probes that must FAIL before the tunnel exists. Asserted on every run,
    #: because a scenario where the target was reachable all along teaches
    #: nothing and would never be noticed otherwise.
    negative: tuple[Probe, ...] = ()

    def spec(self, script: str, assets: str, settle: float) -> dict:
        return {
            'hosts': list(self.hosts),
            'links': [[l.a, l.b, l.net] for l in self.links],
            'services': [[s.host, s.addr, s.port, s.flag] for s in self.services],
            'sshd_on': list(self.sshd_on),
            'sshd_extra': list(self.sshd_extra),
            'routes': [list(r) for r in self.routes],
            'probes': [[p.frm, p.addr, p.port, p.expect, p.name,
                        list(p.socks) if p.socks else None]
                       for p in self.probes],
            'negative': [[p.frm, p.addr, p.port, p.expect, p.name,
                          list(p.socks) if p.socks else None]
                         for p in self.negative],
            'script': script,
            'assets': assets,
            'settle': settle,
        }


@dataclass
class Attempt:
    """What came back from one run."""

    ok: bool = False
    detail: str = ''
    probes: list[dict] = field(default_factory=list)
    script_output: str = ''
    error: str = ''

    @property
    def met(self) -> int:
        return sum(1 for p in self.probes if p.get('ok'))

    @property
    def total(self) -> int:
        return len(self.probes)


# --------------------------------------------------------------------------
# Capability
# --------------------------------------------------------------------------

_NEEDED = ('unshare', 'nsenter', 'ip', 'ssh-keygen')


def capability() -> tuple[bool, str]:
    """(usable, why not). crux D14: when this says no, the track says so.

    Checked by actually creating a namespace rather than by reading a sysctl,
    because the sysctl is one of several ways this can be turned off and the
    only question that matters is whether it works.
    """
    missing = [t for t in _NEEDED if not shutil.which(t)]
    if missing:
        return False, f'missing: {", ".join(missing)}'
    try:
        r = subprocess.run(
            ['unshare', '-Urn', '--map-auto', 'ip', 'link', 'add', 'c0',
             'type', 'veth', 'peer', 'name', 'c1'],
            capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f'{e.__class__.__name__}: {e}'
    if r.returncode:
        why = (r.stderr or r.stdout).strip().splitlines()
        return False, why[-1] if why else 'unshare failed'
    return True, ''


def sshd_path() -> str | None:
    return (shutil.which('sshd') or
            next((c for c in ('/usr/sbin/sshd', '/usr/bin/sshd')
                  if Path(c).exists()), None))


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------

_SSHD_CONFIG = """Port {port}
HostKey {assets}/hostkey
PidFile /tmp/crux-sshd.pid
StrictModes no
PasswordAuthentication no
UsePAM no
AllowTcpForwarding yes
GatewayPorts yes
PermitOpen any
LogLevel ERROR
"""

#: An account database of crux own, bind-mounted over the real one inside the
#: namespace. Not a nicety: sshd read the host `/etc/shadow`, found root
#: locked there, and refused the login. A scenario has to behave the same for
#: every user on every machine, so it brings its own users.
_PASSWD = """root:x:0:0:root:/root:/bin/sh
pivot:x:1000:1000:pivot:/home/pivot:/bin/sh
sshd:x:74:74:sshd:/:/sbin/nologin
nobody:x:65534:65534:nobody:/:/sbin/nologin
"""
_GROUP = 'root:x:0:\npivot:x:1000:\nsshd:x:74:\nnobody:x:65534:\n'
#: Never used: every login is by public key. It exists because sshd checks
#: the account is not locked before it will look at a key at all, and an
#: entry of `!` or `*` counts as locked.
_SHADOW = ('root:$6$crux$unusedplaceholder:20000:0:99999:7:::\n'
           'pivot:$6$crux$unusedplaceholder:20000:0:99999:7:::\n')

_SVC = """import socket
import sys

addr, port, flag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((addr, port))
s.listen(8)
while True:
    c, _ = s.accept()
    c.sendall((flag + chr(10)).encode())
    c.close()
"""


def prepare_assets(root: Path, ssh_port: int = SSH_PORT) -> Path:
    """Everything the namespace side needs, generated once per scenario.

    Idempotent: an existing keypair is reused, because regenerating it would
    invalidate the `-i` path a student has already typed into their script.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / 'empty').mkdir(exist_ok=True)
    (root / 'empty').chmod(0o755)
    etc = root / 'etc'
    etc.mkdir(exist_ok=True)
    (etc / 'passwd').write_text(_PASSWD)
    (etc / 'group').write_text(_GROUP)
    (etc / 'shadow').write_text(_SHADOW)
    (etc / 'shadow').chmod(0o600)
    (root / 'svc.py').write_text(_SVC)
    (root / 'sshd_config').write_text(
        _SSHD_CONFIG.format(port=ssh_port, assets=root))

    if not (root / 'id').exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                        '-C', 'crux', '-f', str(root / 'id')],
                       check=True, capture_output=True)
    if not (root / 'hostkey').exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                        '-C', 'crux-host', '-f', str(root / 'hostkey')],
                       check=True, capture_output=True)
    (root / 'id').chmod(0o600)
    return root


# --------------------------------------------------------------------------
# Host side
# --------------------------------------------------------------------------

def run_attempt(topo: Topology, script: Path, assets: Path,
                settle: float = 2.0) -> Attempt:
    """Build the network, run `script` in the attacker namespace, probe."""
    ok, why = capability()
    if not ok:
        return Attempt(error=f'unprivileged namespaces unavailable: {why}')

    spec = topo.spec(str(script), str(assets), settle)
    argv = ['unshare', '-Urnm', '--map-auto', sys.executable, '-m',
            'crux.targets.netns']
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent.parent)
    try:
        proc = subprocess.run(argv, input=json.dumps(spec), text=True,
                              capture_output=True, timeout=BUILD_TIMEOUT,
                              env=env)
    except subprocess.TimeoutExpired:
        return Attempt(error='the topology did not finish building in time')
    except OSError as e:
        return Attempt(error=f'could not start the builder: {e}')

    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ''
    try:
        data = json.loads(line)
    except ValueError:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return Attempt(error=tail[-1] if tail else 'the builder said nothing')
    return Attempt(ok=data.get('ok', False), detail=data.get('detail', ''),
                   probes=data.get('probes', []),
                   script_output=data.get('script_output', ''),
                   error=data.get('error', ''))


# --------------------------------------------------------------------------
# Namespace side
# --------------------------------------------------------------------------

def _sh(cmd: str) -> None:
    subprocess.run(['sh', '-c', cmd], check=True, capture_output=True)


def _ns(pid: int | None, *args: str, check: bool = True):
    argv = (['nsenter', f'--net=/proc/{pid}/ns/net'] if pid else []) + list(args)
    r = subprocess.run(argv, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'{" ".join(args)}: {r.stderr.strip()}')
    return r


def _hold() -> subprocess.Popen:
    """A process holding a fresh network namespace open.

    It signals readiness down a pipe rather than the caller sleeping: without
    that, `/proc/<pid>/ns/net` is raced against `unshare` and the veth lands
    in the wrong namespace once in every few dozen runs.
    """
    r, w = os.pipe()
    p = subprocess.Popen(['unshare', '-n', 'sh', '-c',
                          f'echo r >&{w}; exec sleep 600'], pass_fds=(w,))
    os.read(r, 1)
    os.close(r)
    os.close(w)
    return p


_DIRECT = '''import socket
try:
    c = socket.create_connection((ADDR, PORT), timeout=4)
    print(c.recv(200).decode("utf-8", "replace").strip())
    c.close()
except OSError as e:
    print("ERR " + e.__class__.__name__)
'''

#: A SOCKS5 CONNECT, by hand. Greeting with "no authentication", then a
#: request carrying the destination as a literal address.
_VIA_SOCKS = r"""import socket
GREET = bytes([5, 1, 0])
OKGREET = bytes([5, 0])
def connect():
    c = socket.create_connection((SHOST, SPORT), timeout=4)
    c.sendall(GREET)
    if c.recv(2) != OKGREET:
        print("ERR socks-greeting"); return
    host = ADDR.encode()
    req = bytes([5, 1, 0, 3, len(host)]) + host + bytes([PORT >> 8, PORT & 0xFF])
    c.sendall(req)
    reply = c.recv(4)
    if len(reply) < 2 or reply[1] != 0:
        print("ERR socks-refused-%d" % (reply[1] if len(reply) > 1 else -1)); return
    n = 4 if reply[3] == 1 else (16 if reply[3] == 4 else c.recv(1)[0])
    c.recv(n); c.recv(2)                      # bound addr and port, discarded
    print(c.recv(200).decode("utf-8", "replace").strip())
    c.close()
try:
    connect()
except OSError as e:
    print("ERR " + e.__class__.__name__)
"""

_PROBE_DIR = Path(os.environ.get('TMPDIR', '/tmp'))


def _probe(pid: int | None, addr: str, port: int, expect: str,
           socks: tuple[str, int] | None = None) -> tuple[bool, str]:
    if socks:
        code = (f'ADDR={addr!r}\nPORT={port}\nSHOST={socks[0]!r}\n'
                f'SPORT={socks[1]}\n' + _VIA_SOCKS)
    else:
        code = f'ADDR={addr!r}\nPORT={port}\n' + _DIRECT
    # Written to a file, not passed with `-c`: the SOCKS request contains NUL
    # bytes, and an argv cannot carry a NUL. The probe body itself is pure
    # ASCII (the NULs are built at runtime from hex escapes), so the file is
    # safe; the argument would not have been.
    fd, name = tempfile.mkstemp(suffix='.py', dir=str(_PROBE_DIR))
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(code)
        r = _ns(pid, sys.executable, name, check=False)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass
    got = r.stdout.strip()
    return (expect in got), got


def main() -> int:
    out: dict = {'ok': False, 'probes': [], 'script_output': '', 'error': ''}
    holders: list[subprocess.Popen] = []
    procs: list[subprocess.Popen] = []
    try:
        spec = json.loads(sys.stdin.read())
        assets = Path(spec['assets'])

        # Make sshd possible: its privsep dir, and an account database that
        # does not depend on whoever is running crux.
        sshd = sshd_path()
        # Per scenario, never appended to the shared asset: the assets
        # directory outlives a run, so appending there would leave one
        # scenario's `AllowTcpForwarding no` switched on for the next one.
        sshd_cfg = assets / 'sshd_config'
        if spec.get('sshd_extra'):
            sshd_cfg = Path(spec['script']).parent / 'sshd_config.run'
            sshd_cfg.write_text((assets / 'sshd_config').read_text() + '\n'
                                + '\n'.join(spec['sshd_extra']) + '\n')
        if spec['sshd_on'] and sshd:
            _sh(f'mount --bind {assets}/empty /usr/share/empty.sshd')
            for f in ('passwd', 'group', 'shadow'):
                _sh(f'mount --bind {assets}/etc/{f} /etc/{f}')
            _sh('mount -t tmpfs tmpfs /home && mkdir -p /home/pivot/.ssh')
            _sh(f'cp {assets}/id.pub /home/pivot/.ssh/authorized_keys && '
                'chown -R 1000:1000 /home/pivot && chmod 700 /home/pivot/.ssh '
                '&& chmod 600 /home/pivot/.ssh/authorized_keys')

        pids: dict[str, int | None] = {ATTACKER: None}
        for host in spec['hosts']:
            if host == ATTACKER:
                continue
            p = _hold()
            holders.append(p)
            pids[host] = p.pid

        _ns(None, 'ip', 'link', 'set', 'lo', 'up')
        for host, pid in pids.items():
            if pid:
                _ns(pid, 'ip', 'link', 'set', 'lo', 'up')

        for i, (a, b, net) in enumerate(spec['links']):
            da, db = f'v{i}a', f'v{i}b'
            _ns(pids[a], 'ip', 'link', 'add', da, 'type', 'veth', 'peer',
                'name', db)
            if pids[b] is not None:
                _ns(pids[a], 'ip', 'link', 'set', db, 'netns', str(pids[b]))
            _ns(pids[a], 'ip', 'addr', 'add', f'{net}.1/24', 'dev', da)
            _ns(pids[a], 'ip', 'link', 'set', da, 'up')
            _ns(pids[b], 'ip', 'addr', 'add', f'{net}.2/24', 'dev', db)
            _ns(pids[b], 'ip', 'link', 'set', db, 'up')

        for host, dest, via in spec['routes']:
            _ns(pids[host], 'ip', 'route', 'add', dest, 'via', via)

        svc_src = assets / 'svc.py'
        for host, addr, port, flag in spec['services']:
            procs.append(subprocess.Popen(
                (['nsenter', f'--net=/proc/{pids[host]}/ns/net']
                 if pids[host] else [])
                + [sys.executable, str(svc_src), addr, str(port), flag],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

        for host in spec['sshd_on']:
            if not sshd:
                out['error'] = 'sshd is not installed'
                break
            procs.append(subprocess.Popen(
                (['nsenter', f'--net=/proc/{pids[host]}/ns/net']
                 if pids[host] else [])
                + [sshd, '-D', '-e', '-f', str(sshd_cfg)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1.2)

        # Negatives first: prove the target really is out of reach before the
        # student does anything, so a scenario that was solvable by accident
        # cannot ship.
        for frm, addr, port, expect, name, socks in spec['negative']:
            hit, got = _probe(pids[frm], addr, port, expect,
                              tuple(socks) if socks else None)
            if hit:
                out['error'] = (f'{addr}:{port} was reachable from {frm} '
                                'before any tunnel existed')
                print(json.dumps(out))
                return 0

        script = Path(spec['script'])
        if script.exists():
            # **Output goes to a file, not to a pipe.** A tunnel script
            # backgrounds things by design, and a backgrounded child inherits
            # the pipe and holds it open, so `capture_output` waits for EOF
            # that never comes and every failed attempt cost a 45-second
            # timeout instead of a two-second answer. A file has no such
            # reader to wait for.
            log = script.parent / '.crux-run.log'
            try:
                with open(log, 'w') as fh:
                    subprocess.run(['sh', str(script)], stdout=fh,
                                   stderr=subprocess.STDOUT, timeout=30,
                                   cwd=str(script.parent))
            except subprocess.TimeoutExpired:
                out['script_output'] = '[crux] the script did not finish in 30s'
            try:
                out['script_output'] = (log.read_text()[-1200:]
                                        or out['script_output'])
            except OSError:
                pass
            time.sleep(float(spec.get('settle', 2.0)))

        results = []
        for frm, addr, port, expect, name, socks in spec['probes']:
            hit, got = _probe(pids[frm], addr, port, expect,
                              tuple(socks) if socks else None)
            results.append({'name': name or f'{addr}:{port}', 'from': frm,
                            'addr': addr, 'port': port, 'ok': hit, 'got': got})
        out['probes'] = results
        out['ok'] = bool(results) and all(p['ok'] for p in results)
        if not out['ok']:
            first = next((p for p in results if not p['ok']), None)
            if first:
                out['detail'] = (f'{first["name"]} did not answer from '
                                 f'{first["from"]}: {first["got"] or "nothing"}')
        else:
            out['detail'] = 'the path is open.'
    except Exception as e:                                    # noqa: BLE001
        out['error'] = f'{e.__class__.__name__}: {e}'
    finally:
        for p in procs + holders:
            try:
                p.terminate()
            except OSError:
                pass
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
