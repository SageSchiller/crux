"""You already hold more than the account you logged in as.

Group membership is transitive and nobody keeps a mental model of it. An
account is put in a support group, that group is nested inside an operations
group for a ticketing reason nobody remembers, and the operations group
administers half the estate. Nothing in the account's own record says so.

The first move here costs nothing at all if you read what you hold, and the
scenario is built so that the tempting alternative is to start buying rights
you did not need. Three workstations look identical from the outside; only one
of them has anybody on it, and which one is a fact the collection already
carries.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('tier2', 'group', name='SUPPORT TIER 2',
             note='second-line support'),
        Node('wksadmins', 'group', name='WORKSTATION ADMINS',
             note='local administrators on the desktop estate'),
        Node('wk1', 'computer', note='a workstation'),
        Node('wk2', 'computer', note='a workstation'),
        Node('wk3', 'computer', note='a workstation'),
        Node('temp', 'user', note='an account, like any other'),
        Node('admin', 'user', note='an account, like any other'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('reporting', 'group', name='FINANCE REPORTING',
             note='reads the finance share'),
        Node('svcprint', 'user', name='svc_print',
             note='service account, drives the print queues'),
    ),
    edges=(
        Right('you', 'tier2', 'MemberOf'),
        Right('tier2', 'wksadmins', 'MemberOf',
              why='the nested membership that made the whole desktop estate '
                  'yours before you spent anything'),
        Right('wksadmins', 'wk1', 'AdminTo'),
        Right('wksadmins', 'wk2', 'AdminTo',
              why='the one of the three with somebody on it'),
        Right('wksadmins', 'wk3', 'AdminTo'),
        Right('wk1', 'temp', 'HasSession',
              why='a session, and the account it belongs to holds nothing'),
        Right('wk2', 'admin', 'HasSession',
              why='the session this whole collection turns on'),
        Right('admin', 'da', 'MemberOf'),
        Right('you', 'reporting', 'WriteDacl',
              why='a right you hold over a group that administers nothing'),
        Right('you', 'svcprint', 'ForceChangePassword',
              why='resetting a service account password, which breaks the '
                  'print queues and reaches nothing'),
    ),
    owned=('you',),
    objective='da',
)

SCENARIOS = [
    Scenario(
        id='lineage-nested',
        track='lineage',
        title='Three workstations, one of them occupied',
        tier='graded',
        order=30,
        waypoint='ad-enum',
        body=LineageBody(
            brief='A collection of a domain you have one account in. **Own '
                  'DOMAIN ADMINS.** Read what you already hold before you buy '
                  'anything: press **m**.',
            graph=GRAPH,
            teaches='nesting',
            objective_note='Membership of DOMAIN ADMINS.',
            debrief='The account you logged in as is in one support group. '
                    'That group is inside another, and the second one '
                    'administers every workstation in the estate. **Nothing on '
                    'the account itself says so**, and that is the normal '
                    'condition: memberships nest for reasons nobody records, '
                    'and the effective set is almost always larger than the '
                    'one anybody would name from memory. Reading it is free. '
                    'The rest of the exercise is that three workstations look '
                    'identical and only one of them has anybody logged into '
                    'it, which is also something the collection told you '
                    'before you connected to any of them.',
        ),
    ),
]
