"""The interesting-looking branch that does not go anywhere.

Every collection has one: a right over something that sounds like the crown
jewels, which turns out to lead to a host nobody else is on and nothing else
trusts. Following it is not a mistake of technique, it is a mistake of reading:
the branch was always a cul-de-sac and the collection said so.

The route that does arrive goes through a group whose name promises nothing.
That is the shape this scenario exists to drill, and it is the same instinct
`sift` trains one layer down: the thing that looks like the lead is not the
lead, and the boring line is.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('tier1', 'group', name='SERVICE DESK TIER 1',
             note='first-line support'),
        Node('svcsql', 'user', name='svc_mssql',
             note='service account, runs the database engine'),
        Node('sqlhost', 'computer', host='db', note='a database server'),
        Node('dcmaint', 'group', name='DC MAINTENANCE',
             note='local administrators on the domain controllers'),
        Node('dc', 'computer', host='dc', note='a domain controller'),
        Node('admin', 'user', note='an account, like any other'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('svcmon', 'user', name='svc_monitor',
             note='service account, collects metrics'),
        Node('monhost', 'computer', host='server', note='a monitoring server'),
        Node('reporting', 'group', name='REPORT READERS',
             note='reads the reporting share'),
        Node('jump', 'computer', host='server', note='a jump host'),
    ),
    edges=(
        Right('you', 'tier1', 'MemberOf'),
        Right('you', 'svcsql', 'GenericWrite',
              why='full write over the database service account, which is the '
                  'most valuable-looking right in this collection and the '
                  'start of a branch that never reaches the objective'),
        Right('svcsql', 'sqlhost', 'SQLAdmin',
              why='administrator inside the database, and nothing beyond it: '
                  'nobody is logged into this host and nothing else trusts it'),
        Right('tier1', 'dcmaint', 'AddMember',
              why='an unremarkable group name, and the only right in this '
                  'collection that puts you on a domain controller'),
        Right('dcmaint', 'dc', 'AdminTo',
              why='local administrator on a domain controller'),
        Right('dc', 'admin', 'HasSession',
              why='the session that was always the point of reaching the '
                  'controller'),
        Right('admin', 'da', 'MemberOf'),
        Right('tier1', 'svcmon', 'WriteOwner',
              why='take ownership, then grant, then use: three writes to '
                  'reach the same place a cheaper right already reaches'),
        Right('svcmon', 'monhost', 'AdminTo'),
        Right('monhost', 'admin', 'HasSession'),
        Right('tier1', 'jump', 'CanPSRemote',
              why='a shell on a jump host, which is the cheapest thing on the '
                  'board and connects to nothing else in this collection'),
        Right('tier1', 'reporting', 'WriteDacl',
              why='rewrite the permissions on a group that administers '
                  'nothing'),
    ),
    owned=('you',),
    objective='da',
)

SCENARIOS = [
    Scenario(
        id='lineage-culdesac',
        track='lineage',
        title='The right that looks like the way in',
        tier='graded',
        order=20,
        waypoint='ad-acl-abuse',
        body=LineageBody(
            brief='A collection of a domain you have one account in. **Own '
                  'DOMAIN ADMINS.** Two branches out of what you hold lead '
                  'somewhere; one of them does not. Press **m** to read the '
                  'collection first.',
            graph=GRAPH,
            teaches='reach',
            objective_note='Membership of DOMAIN ADMINS.',
            debrief='Full write over the database service account is the '
                    'strongest-sounding right on this map and it is a '
                    'cul-de-sac: it reaches a host nobody is logged into and '
                    'nothing else trusts, and the collection said so before '
                    'you spent anything. **Reading a graph is mostly reading '
                    'what is not on it.** The route that arrives runs through '
                    'a group whose name promises nothing at all, which is the '
                    'normal case, because groups are named after the paperwork '
                    'that created them and not after what they can do. The '
                    'other arriving route works too and takes ownership of an '
                    'object to get there, three writes where one would have '
                    'done.',
        ),
    ),
]
