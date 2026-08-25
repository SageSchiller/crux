"""Two ways onto the same host: read the password, or reset one.

LAPS puts a rotating local-administrator password in a directory attribute, and
the right to read it is exactly as strong as the right to reset an account, and
enormously quieter: reading an attribute you were granted leaves nothing at
all, while a password reset is a write, an event, and a locked-out user. This
collection makes them cost the *same* on paper, so the number does not decide
it and the noise does.

This is the `quiet` scenario: the cheapest route and a louder route that also
arrives are the same price, and the whole choice is what you leave behind.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('laps', 'group', name='LAPS READERS',
             note='can read managed local-admin passwords'),
        Node('resetters', 'group', name='ACCOUNT OPERATORS',
             note='can reset ordinary user passwords'),
        Node('fileserver', 'computer', host='server', note='a file server'),
        Node('dbadmin', 'user', name='sql_admin',
             note='a database administrator'),
        Node('dba', 'group', name='DATABASE ADMINS'),
        Node('dbhost', 'computer', host='db', note='the production database'),
        Node('svcreport', 'user', name='svc_report',
             note='service account, runs the reporting jobs'),
        Node('reporting', 'group', name='REPORT WRITERS'),
        Node('contractor', 'user', note='an account, like any other'),
    ),
    edges=(
        Right('you', 'laps', 'MemberOf'),
        Right('you', 'resetters', 'MemberOf'),
        Right('laps', 'fileserver', 'ReadLAPSPassword',
              why='read the local administrator password straight out of the '
                  'directory. Nothing is written, nothing rotates early, and '
                  'no user is locked out: the quiet way onto the host'),
        Right('resetters', 'dbadmin', 'ForceChangePassword',
              why='reset a real administrator password to reach the same '
                  'estate. It costs the same on paper and leaves a locked-out '
                  'DBA and an event behind it'),
        Right('fileserver', 'dbadmin', 'HasSession',
              why='the administrator is logged into the file server, so the '
                  'quiet route reaches them without touching their password'),
        Right('dbadmin', 'dba', 'MemberOf'),
        Right('dba', 'dbhost', 'AdminTo',
              why='the objective the whole collection is pointed at'),
        Right('you', 'svcreport', 'GenericWrite',
              why='write over a reporting service account that reaches only '
                  'the reporting group'),
        Right('svcreport', 'reporting', 'AddMember'),
        Right('resetters', 'contractor', 'ForceChangePassword',
              why='the reset right pointed at somebody who holds nothing'),
    ),
    owned=('you',),
    objective='dbhost',
)

SCENARIOS = [
    Scenario(
        id='lineage-laps',
        track='lineage',
        title='Read the password, or reset one',
        tier='graded',
        order=50,
        waypoint='ad-cred-access',
        body=LineageBody(
            brief='A collection of a domain you have one account in. **Own '
                  'the production database host.** Two routes reach the same '
                  'administrator for the same cost. Press **m** to read the '
                  'collection before you choose.',
            graph=GRAPH,
            teaches='quiet',
            objective_note='Local administrator on the production database.',
            debrief='Both routes cost the same, so the number cannot decide '
                    'this one. Reading a LAPS password is a **read**: you were '
                    'granted the attribute, you read it, and nothing in the '
                    'directory changes. Resetting the administrator\'s '
                    'password is a **write**: an event on a controller, a '
                    'rotation, and a real person who can no longer log in and '
                    'is about to call somebody. **Cost and noise are '
                    'different axes**, and a student who only ever minimises '
                    'the number will, sooner or later, take a route that is '
                    'exactly as cheap and leaves a mess. On an assessment the '
                    'mess is a finding against you; on a real engagement it is '
                    'how you get caught.',
        ),
    ),
]
