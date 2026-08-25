"""The whole domain is one command, once you can reach the replication right.

DCSync is the end state everything else on a domain graph is walking towards:
the right to replicate the directory and pull every hash in it, the local
administrator and the domain administrator alike. It is one edge, priced at
one, and the exercise is not using it but *reaching* it, because the account
that holds it is never you and the route there is where the reading happens.

The trap is a route that reaches Domain Admins the obvious way and stops there,
looking finished, while the objective is a hash the DCSync route hands you and
the group-membership route does not.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('secops', 'group', name='SECURITY OPERATIONS',
             note='administers the tiering and the audit tooling'),
        Node('svcaudit', 'user', name='svc_audit',
             note='service account, reads the directory for the SIEM'),
        Node('krbtgt', 'user', name='krbtgt',
             note='the account whose hash signs every ticket in the domain'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('tieradmins', 'group', name='TIER 0 ADMINS'),
        Node('pkiadmin', 'user', name='pki_admin',
             note='runs the certificate authority'),
        Node('dc', 'computer', host='dc', note='a domain controller'),
        Node('jumphost', 'computer', host='server', note='a jump host'),
    ),
    edges=(
        Right('you', 'secops', 'MemberOf'),
        Right('secops', 'svcaudit', 'GenericAll',
              why='full control of the SIEM reader account, the start of the '
                  'route that actually finishes the job'),
        Right('svcaudit', 'dc', 'DCSync',
              why='replicate the directory and pull every hash in it, krbtgt '
                  'included. One command, and the domain is yours in a way a '
                  'group membership is not: this is the objective'),
        Right('dc', 'krbtgt', 'HasSession',
              why='krbtgt does not log in, but replicating the controller '
                  'yields its hash all the same: this is what DCSync hands '
                  'you and a group membership never does'),
        Right('secops', 'tieradmins', 'AddMember',
              why='add yourself to a tier-0 group, which reaches DOMAIN '
                  'ADMINS and looks like the finish line'),
        Right('tieradmins', 'da', 'MemberOf',
              why='DOMAIN ADMINS: the group people stop at, one step short of '
                  'the hash that survives a password reset'),
        Right('secops', 'pkiadmin', 'WriteOwner',
              why='take ownership of the CA admin, a longer route to the same '
                  'group and no closer to krbtgt'),
        Right('pkiadmin', 'tieradmins', 'MemberOf'),
        Right('secops', 'jumphost', 'CanPSRemote',
              why='a shell on a jump host that trusts nothing else'),
    ),
    owned=('you',),
    objective='krbtgt',
)

SCENARIOS = [
    Scenario(
        id='lineage-dcsync',
        track='lineage',
        title='Domain Admin is not the objective',
        tier='graded',
        order=60,
        waypoint='ad-dcsync',
        body=LineageBody(
            brief='A collection of a domain you have one account in. **Own '
                  'krbtgt** -- the account whose hash signs every ticket in '
                  'the domain, and the one that survives a password reset. '
                  'Reaching DOMAIN ADMINS is not the same thing. Press **m** '
                  'to read the collection.',
            graph=GRAPH,
            teaches='reach',
            objective_note='Control of the krbtgt hash, via replication.',
            debrief='DCSync is one edge and it is the end state the whole '
                    'graph walks toward: replicate the directory and pull '
                    'every hash, krbtgt included. The exercise is never using '
                    'it, it is **reaching** it, because the account that holds '
                    'it is never the one you start as. The trap is the route '
                    'that reaches DOMAIN ADMINS and stops, looking finished: '
                    'membership of that group is real power and it is also '
                    'revocable, resettable, and gone the morning after '
                    'someone notices. The krbtgt hash is none of those things. '
                    '**Knowing what you are actually trying to hold, rather '
                    'than the most impressive-sounding group on the way to '
                    'it, is the judgement here.**',
        ),
    ),
]
