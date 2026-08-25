"""Chain mode: Aldwych, the domain from the outside in to Domain Admin.

The third engagement, and the one that carries the story all the way to the
end. Wexler is a single Linux host; Northwind reaches the directory and stops
there, on the observation that reaching LDAP is where the domain half of the
exam actually begins. This engagement begins where Northwind ended and finishes
the job: it is the only chain with a fourth stage, and that stage is `lineage`.

Four stages, one account carried through all of them. An anonymous LDAP dump
turns up a service account with its password sitting in a `description` field;
those credentials land a template injection on an internal self-service app
whose public proof-of-concept was written against the previous minor version;
the foothold that gives you can reach the domain controller a pivot away; and
with the directory collected, the graph from that same service account to
Domain Admins is not the shortest path BloodHound will draw for you.

Everything is fictional and runs on loopback or in namespaces crux built
(crux D7, D23). The password-in-description, the endpoint that moved between
versions, the port typo'd in a forward, and the cheapest-is-not-shortest graph
are all real.
"""

from __future__ import annotations

from ...model import Action, ChainBody, ConduitBody, LineageBody, MarkBody
from ...model import SalvageBody, Scenario, Stage
from ...targets._fixture import DirUser, LdapUsers
from ...targets._graph import Domain, Node, Right
from ...targets._hits import Requirement
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# Stage 1 - sift: a password in a directory attribute
# --------------------------------------------------------------------------

_STAGE1 = MarkBody(
    prompt='An anonymous LDAP bind against the domain controller returned the '
           'directory. Mark every line that changes what you do next.',
    fixture=LdapUsers(
        domain='aldwych.local',
        users=(
            DirUser('svc_deploy',
                    'Deploy automation - Pwd Autumn2024! rotate quarterly',
                    kind='lead',
                    why='A password in a `description` needs no cracking, no '
                        'roasting and no second host. It is a working '
                        'credential the moment you read it, and service '
                        'accounts are where they get left because a person '
                        'set the account up and a person had to remember it.'),
            DirUser('svc_web', 'IIS application pool',
                    flags='DONT_REQ_PREAUTH', kind='decoy',
                    why='AS-REP roasting is a real lead and a slower one: it '
                        'yields a hash you still have to crack offline, and '
                        'there is a plaintext password two lines up that needs '
                        'none of that.'),
            DirUser('a.finch', 'Domain Admin - do not disable', kind='decoy',
                    why='Knowing which account is privileged is not the same '
                        'as holding it. This line tells you where you are '
                        'going, not how to get there, and marking it as the '
                        'way in is the classic confusion of target for route.'),
        ),
    ),
    actions=(
        Action('Authenticate as svc_deploy with the password from its '
               'description.', True,
               'A credential in a `description` is a working login the moment '
               'you read it: no hash, no crack, no second host. That is the '
               'foothold, and it is faster than everything else on the '
               'screen.'),
        Action('AS-REP-roast svc_web and crack the hash offline.',
               why='A real technique and the slower one here. It hands you a '
                   'hash to crack when a plaintext password is already sitting '
                   'in the dump.'),
        Action('RID-cycle the domain through the null session for more '
               'usernames.',
               why='Enumeration, not a way in. More names do not help when you '
                   'already hold a working credential.'),
    ),
)

# --------------------------------------------------------------------------
# Stage 2 - salvage: the endpoint moved a version
# --------------------------------------------------------------------------

_S2_BROKEN = r'''#!/usr/bin/env python3
# Aldwych Self-Service 4.1 - server-side template injection in the exporter
# (fictional target, real defect class). Authenticated as svc_deploy.
import urllib.request
import urllib.parse
import urllib.error

TARGET = "{{URL}}"
# a template expression the exporter evaluates server-side
PAYLOAD = "#{ 7*7 }__CRUX-EXEC__"

def main():
    # this PoC was written for 4.0, where the exporter lived at /api/v1/export
    # and took a "template" field
    data = urllib.parse.urlencode({"template": PAYLOAD, "format": "pdf"})
    req = urllib.request.Request(TARGET + "/api/v1/export",
                                 data=data.encode())
    try:
        body = urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
    print("[*] response: " + body)
    print("[+] landed" if "CRUX-LANDED" in body else "[-] no")

if __name__ == "__main__":
    main()
'''

_S2_SOLUTION = (_S2_BROKEN
                .replace('/api/v1/export', '/api/v2/export')
                .replace('{"template": PAYLOAD', '{"tpl": PAYLOAD'))

_STAGE2 = SalvageBody(
    brief='The svc_deploy credentials log in to the Aldwych self-service app, '
          'whose exporter evaluates a template server-side. The public '
          'proof-of-concept was written for version 4.0: it posts to '
          '`/api/v1/export` with a `template` field. This is 4.1, where the '
          'exporter moved to `/api/v2/export` and the field was renamed '
          '`tpl`. The payload itself is fine.',
    filename='aldwych_export.py',
    defects=('the endpoint moved between minor versions',
             'the injected field was renamed'),
    cve='', models='a self-service reporting app',
    real_note=(
        'An exploit is written against one version and the target is running '
        'another. Endpoints get versioned, parameters get renamed, and a '
        'proof-of-concept that was correct six months ago posts a perfect '
        'payload at a 404. The injection logic here never changed; only where '
        'to send it did, which is why reading the app in front of you beats '
        'trusting the script written for the last one.'
    ),
    route='/api/v2/export', reject_code=404, reject_message='not found',
    broken=_S2_BROKEN, solution=_S2_SOLUTION,
    requirements=(
        Requirement('the method', 'method', 'POST',
                    hint='the exporter takes a POST'),
        Requirement('the moved endpoint', 'route', '/api/v2/export',
                    hint='nothing arrived at /api/v2/export; the PoC is still '
                         'posting to the 4.0 path'),
        Requirement('the renamed field', 'form', '__CRUX-EXEC__', key='tpl',
                    hint='the injection did not arrive in a field called '
                         '`tpl`, which is what 4.1 renamed `template` to'),
    ),
    debrief='**A perfect payload at the wrong endpoint is a 404, and a 404 is '
            'not a bug in your payload.** Both defects were version drift: the '
            'route moved from v1 to v2 and the field from `template` to `tpl` '
            'between 4.0 and 4.1. The injection string was correct the whole '
            'time. Finding it meant reading the version of the app actually in '
            'front of you rather than the one the proof-of-concept was written '
            'against.',
)

# --------------------------------------------------------------------------
# Stage 3 - conduit: the domain controller is a pivot away
# --------------------------------------------------------------------------

_S3_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'app01', 'dc01'),
    links=(Link(ATTACKER, 'app01', '10.9.0'), Link('app01', 'dc01', '10.9.1')),
    services=(Service('dc01', '10.9.1.2', 389, 'ALDWYCH-DC-LDAP'),),
    sshd_on=('app01',),
    negative=(Probe(ATTACKER, '10.9.1.2', 389, 'ALDWYCH',
                    'the domain controller, reached directly'),),
    probes=(Probe(ATTACKER, '127.0.0.1', 389, 'ALDWYCH-DC-LDAP',
                  'the domain controller LDAP on 127.0.0.1:389'),),
)

_S3_STARTER = r'''#!/bin/sh
# The template injection gave you a shell on app01 (10.9.0.2) and an SSH key.
#
#   you 10.9.0.1  <-->  10.9.0.2 app01 10.9.1.1  <-->  10.9.1.2 dc01
#
# dc01 is the domain controller. Its LDAP on 10.9.1.2:389 answers only from
# app01. You want to collect the directory, which means reaching it from here.
#
# Make it answer on 127.0.0.1:389 on your box.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

# the destination port is a typo
$SSH -L 389:10.9.1.2:3389 pivot@10.9.0.2
'''

_S3_SOLUTION = _S3_STARTER.replace('-L 389:10.9.1.2:3389',
                                   '-L 389:10.9.1.2:389')

_STAGE3 = ConduitBody(
    brief='dc01 runs the directory on `10.9.1.2:389` and answers only from '
          'app01, where you have a shell. Forward it to `127.0.0.1:389` on '
          'your own box so your collector can reach it. The script runs '
          'without an error and the port answers nothing.',
    filename='dc_tunnel.sh',
    starter=_S3_STARTER, solution=_S3_SOLUTION,
    topology=_S3_TOPOLOGY,
    debrief='**The forward built cleanly and delivered nothing, because the '
            'destination port was wrong.** `ExitOnForwardFailure` catches a '
            'local bind it cannot make; it cannot catch a far-end port that '
            'nothing is listening on, so `-L 389:10.9.1.2:3389` gives you a '
            'listener on `127.0.0.1:389` that forwards into a closed port and '
            'never reports a thing. The destination is `389`, the port the '
            'directory is actually on. A tunnel that opens is not the same as '
            'a tunnel that reaches.',
)

# --------------------------------------------------------------------------
# Stage 4 - lineage: the graph from svc_deploy to Domain Admins
# --------------------------------------------------------------------------

_S4_GRAPH = Domain(
    nodes=(
        Node('you', 'user', name='svc_deploy',
             note='the account whose password was in the directory'),
        Node('appsupport', 'group', name='APP SUPPORT',
             note='administers the application servers'),
        Node('helpdesk', 'group', name='HELPDESK', note='password resets'),
        Node('ws', 'computer', note='an administrator workstation'),
        Node('admin', 'user', name='t.hollis',
             note='an account, like any other'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('dbteam', 'group', name='DATABASE ADMINS'),
        Node('svcsql', 'user', name='svc_sql',
             note='service account, runs the reporting database'),
        Node('sqlhost', 'computer', host='db', note='the reporting database'),
        Node('contractor', 'user', note='an account, like any other'),
        Node('spare', 'computer', note='a spare workstation'),
    ),
    edges=(
        Right('you', 'appsupport', 'MemberOf'),
        Right('you', 'helpdesk', 'MemberOf'),
        Right('helpdesk', 'admin', 'ForceChangePassword',
              why='the route BloodHound draws first: three edges to Domain '
                  'Admins, and the one that resets a real administrator, locks '
                  'them out and writes an event to the controller'),
        Right('appsupport', 'ws', 'AdminTo',
              why='you already administer this workstation: one connection, '
                  'nothing written'),
        Right('ws', 'admin', 'HasSession',
              why='the administrator is logged into a box you own, so you '
                  'reach the same account without touching its password'),
        Right('admin', 'da', 'MemberOf'),
        Right('appsupport', 'svcsql', 'GenericAll',
              why='full control of the database service account, which reaches '
                  'a database server and, from there, nothing that helps'),
        Right('svcsql', 'dbteam', 'MemberOf'),
        Right('dbteam', 'sqlhost', 'AdminTo',
              why='administrator on the reporting database, a dead end for '
                  'this objective'),
        Right('helpdesk', 'contractor', 'ForceChangePassword',
              why='the reset right pointed at somebody who holds nothing'),
        Right('appsupport', 'spare', 'CanRDP',
              why='a desktop on a spare box that trusts nothing else'),
    ),
    owned=('you',),
    objective='da',
    domain='aldwych.local', netbios='ALDWYCH',
)

_STAGE4 = LineageBody(
    brief='The directory collected. You are **svc_deploy**, and the objective '
          'is **DOMAIN ADMINS**. The shortest path on the graph is not the '
          'cheapest one. Press **m** to read the collection before you spend '
          'anything.',
    graph=_S4_GRAPH,
    teaches='cost',
    objective_note='Membership of DOMAIN ADMINS.',
    debrief='**This is where the whole engagement was going, and it ends on '
            'the track\'s central claim.** BloodHound will draw you the '
            'three-edge path: helpdesk resets the administrator, you become '
            'them, they are a Domain Admin. It arrives, and it resets a real '
            'person\'s password to do it. The cheaper route is one edge '
            'longer and touches nothing: you already administer a workstation '
            'the administrator is logged into, so you take the session and '
            'the account with it. Fewer edges is not cheaper. It is just '
            'fewer edges, and the difference between the two routes is the '
            'difference between a quiet finish and a phone call to a help '
            'desk.',
)

# --------------------------------------------------------------------------

SCENARIOS = [
    Scenario(
        id='chain-aldwych', track='chain', tier='verified', order=30,
        title='The Aldwych engagement',
        waypoint='ad-acl-abuse',
        source=f'{PLAYBOOK}/14 - Common PEN-200 Attack Chains.md',
        body=ChainBody(
            brief='**Aldwych Financial: a domain, and Domain Admin at the end '
                  'of it.** This engagement does not stop at a foothold or at '
                  'a route to the directory. Read what the directory hands '
                  'you, turn it into a shell, pivot until you can collect the '
                  'domain, and then take the cheapest path through the graph '
                  'to Domain Admins, which is rarely the shortest one.',
            stages=(
                Stage('sift', _STAGE1, title='Aldwych: what the directory says',
                      bridge='The bind returned the directory.'),
                Stage('salvage', _STAGE2, title='Aldwych: foothold',
                      bridge='**svc_deploy\'s password was in its description, '
                             'and it logs in to the self-service app.** The '
                             'app\'s exporter evaluates a template '
                             'server-side, and the public proof-of-concept is '
                             'below. It was written for the previous version '
                             'and reports nothing.'),
                Stage('conduit', _STAGE3, title='Aldwych: reach the domain',
                      needs=('ssh', 'sshd', 'ip'),
                      bridge='**The injection gave you a shell on app01 and an '
                             'SSH key.** `ip addr` shows a second interface on '
                             '`10.9.1.0/24`, and `dc01` sits on it at '
                             '`10.9.1.2` running the directory on 389. Your '
                             'collector cannot reach it from here. Forward '
                             'it.'),
                Stage('lineage', _STAGE4, title='Aldwych: the path to Domain '
                      'Admin',
                      bridge='**The forward is up and you collected the '
                             'domain.** Here is the graph from svc_deploy, the '
                             'account you have held since the first stage, to '
                             'DOMAIN ADMINS. There is more than one way there. '
                             'Take the one that costs least, not the one with '
                             'the fewest edges.'),
            ),
            debrief='**A whole Active Directory engagement, outside in.** A '
                    'password left in a directory attribute, an exploit '
                    'written for the wrong version, a forward with a typo in '
                    'the destination port, and a graph whose shortest path '
                    'was its loudest. None of the four is exotic, and all '
                    'four are where real domain compromises are actually '
                    'won and lost.\n\n'
                    'The through-line is the thing worth keeping: every stage '
                    'rewarded reading what was in front of you over trusting '
                    'the obvious move. The lead that needed no cracking, the '
                    'version actually deployed, the port the service was '
                    'really on, and the route that was cheaper because it '
                    'wrote nothing. That is the judgement the whole of crux '
                    'exists to drill, threaded through one box from the first '
                    'bind to Domain Admin.',
        ),
    ),
]
