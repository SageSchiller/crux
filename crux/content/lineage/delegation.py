"""Constrained delegation: the right that does not look like a path.

Delegation is the edge people walk past, because it does not read like one.
`AllowedToDelegate` is a property on a service account, not an arrow pointing at
Domain Admin, and it takes a moment to see that impersonating *into* a service
means everything that service can reach is now yours. This collection puts the
only route to the domain through a delegation edge, and surrounds it with rights
that look far more like the way in and lead nowhere: full control of a backup
account, ownership of the certificate host, a desktop on a spare box.

It is a `reach` scenario, not a `cost` one, and that classification is itself a
small lesson. To *use* a service account's delegation you must first control
the account, which is a write, so the delegation route is a write plus the
delegation and can never be the single cheapest edge on the board. What makes
it worth taking is not that it is cheap. It is that it is the only thing here
that arrives at all.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('devs', 'group', name='APP DEVELOPERS',
             note='owns the build and deploy service accounts'),
        Node('svcweb', 'user', name='svc_web',
             note='service account, runs the intranet app pool'),
        Node('dc', 'computer', host='dc', note='a domain controller'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('svcbak', 'user', name='svc_backup',
             note='service account, runs the nightly backup'),
        Node('buildsrv', 'computer', host='server', note='the build server'),
        Node('ca', 'computer', host='server',
             note='the certificate authority host'),
        Node('pkiadmin', 'user', name='pki_admin', note='runs the CA'),
        Node('spare', 'computer', host='workstation', note='a spare desktop'),
    ),
    edges=(
        Right('you', 'devs', 'MemberOf'),
        Right('devs', 'svcweb', 'GenericWrite',
              why='write the web service account: the necessary first half of '
                  'the only route that arrives, and a write, which is why this '
                  'route is not the cheapest single edge on the board'),
        Right('svcweb', 'dc', 'AllowedToDelegate',
              why='the account is trusted to impersonate any user to the '
                  'controller service, so it reaches the controller as whoever '
                  'it likes. The edge that does not look like a path until you '
                  'have seen one do this'),
        Right('dc', 'da', 'MemberOf'),
        Right('devs', 'svcbak', 'GenericAll',
              why='full control of the backup account, which is the '
                  'strongest-sounding right here and reaches only a build '
                  'server nobody is logged into'),
        Right('svcbak', 'buildsrv', 'AdminTo',
              why='administrator on a build server that trusts nothing else'),
        Right('devs', 'ca', 'Owns',
              why='you own the certificate-authority host object, which sounds '
                  'catastrophic and, in this collection, leads nowhere: the '
                  'CA admin is a dead end'),
        Right('ca', 'pkiadmin', 'HasSession'),
        Right('devs', 'spare', 'CanRDP',
              why='a desktop on a spare box, the cheapest thing on the board '
                  'and connected to nothing'),
    ),
    owned=('you',),
    objective='da',
)

SCENARIOS = [
    Scenario(
        id='lineage-delegation',
        track='lineage',
        title='The service account that is trusted too far',
        tier='graded',
        order=40,
        waypoint='ad-delegation',
        body=LineageBody(
            brief='A collection of a domain you develop applications in. '
                  '**Own DOMAIN ADMINS.** The strongest-looking rights here go '
                  'nowhere. Press **m** to read the collection.',
            graph=GRAPH,
            teaches='reach',
            objective_note='Membership of DOMAIN ADMINS.',
            debrief='Only one route arrives, and it runs through a delegation '
                    'edge that does not read as a path on the map: '
                    'delegation is a property on a service account, not an '
                    'arrow at Domain Admin, and an account trusted to '
                    'impersonate anyone to the controller service reaches the '
                    'controller as anyone it likes. Everything that *does* '
                    'look like a path is a dead end: full control of the '
                    'backup account reaches a build server nobody is on, '
                    'owning the CA host reaches an administrator who '
                    'administers nothing here. **The strongest-sounding right '
                    'is not the same as the one that goes somewhere**, and '
                    'delegation is the case that proves it, because it barely '
                    'looks like a right at all.',
        ),
    ),
]
