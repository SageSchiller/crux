"""The password reset a collection tool will hand you, and the route past it.

The whole track's argument, in one graph. There are two ways to the same
administrator: three edges through a password reset, or four edges through a
workstation somebody is logged into. A tool that ranks paths by edge count
draws the first one, and on a real engagement the first one means resetting a
named person's password: destructive, logged, and a phone call to a help desk.

**The wrong answer still arrives**, and that is deliberate. A trap that fails
outright teaches "do not press that"; a trap that works and costs more teaches
the thing that actually transfers, which is that arriving is not the only
thing being measured.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', note='the account your shell runs as'),
        Node('helpdesk', 'group', name='HELPDESK', note='password resets'),
        Node('itsupport', 'group', name='IT SUPPORT',
             note='builds and images workstations'),
        Node('wkstn', 'computer', note='a workstation'),
        Node('admin', 'user', note='an account, like any other'),
        Node('da', 'group', name='DOMAIN ADMINS'),
        Node('srvadmins', 'group', name='SERVER ADMINS',
             note='administers the server estate'),
        Node('sqlhost', 'computer', host='db', note='a database server'),
        Node('fileserver', 'computer', host='server', note='a file server'),
        Node('contractor', 'user', note='an account, like any other'),
        Node('spare1', 'computer', note='a workstation'),
        Node('spare2', 'computer', note='a workstation'),
    ),
    edges=(
        Right('you', 'helpdesk', 'MemberOf'),
        Right('you', 'itsupport', 'MemberOf'),
        Right('helpdesk', 'admin', 'ForceChangePassword',
              why='the shortest route on the map, and the one that ends with '
                  'a real person locked out of their account'),
        Right('helpdesk', 'contractor', 'ForceChangePassword',
              why='the same right pointed at somebody who holds nothing'),
        Right('itsupport', 'wkstn', 'AdminTo',
              why='one connection, nothing written, nothing broken'),
        Right('wkstn', 'admin', 'HasSession',
              why='the same account, reached without touching its password'),
        Right('admin', 'da', 'MemberOf'),
        Right('srvadmins', 'sqlhost', 'AdminTo'),
        Right('srvadmins', 'fileserver', 'AdminTo'),
        Right('contractor', 'srvadmins', 'MemberOf'),
        Right('itsupport', 'spare1', 'CanRDP',
              why='a desktop on a machine with nobody on it, which is what '
                  'most of the estate is'),
        Right('itsupport', 'spare2', 'CanRDP',
              why='another desktop with nobody on it. The collection listed '
                  'its sessions, or the absence of them, before you '
                  'connected'),
        Right('helpdesk', 'sqlhost', 'GenericAll',
              why='full control of a database server, which sounds like the '
                  'way in and leads nowhere from here'),
    ),
    owned=('you',),
    objective='da',
)

SCENARIOS = [
    Scenario(
        id='lineage-reset',
        track='lineage',
        title='Two ways to the same administrator',
        tier='graded',
        order=10,
        waypoint='ad-acl-abuse',
        body=LineageBody(
            brief='You have a shell as an ordinary account and a collection of '
                  'the domain. **Own DOMAIN ADMINS.** Press **m** to read the '
                  'collection before you spend anything.',
            graph=GRAPH,
            teaches='cost',
            objective_note='Membership of DOMAIN ADMINS, however you get it.',
            debrief='Both routes arrive. One of them resets a named person\'s '
                    'password, which is irreversible, logged, and the fastest '
                    'way to turn a quiet engagement into a conversation with '
                    'the client. The other connects to a workstation you '
                    'already administer and takes the same account out of its '
                    'memory. **A map that ranks routes by how many edges they '
                    'have will draw you the first one**, because a reset and a '
                    'group membership are one edge each, and one of them is '
                    'free. Counting edges is not the same as counting cost, '
                    'and the difference is the whole of this track.',
        ),
    ),
]
