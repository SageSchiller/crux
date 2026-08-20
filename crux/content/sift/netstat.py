"""sift: reading listening sockets.

Three scenarios. The reading problem here is a comparison rather than a
pattern: the value of this output is entirely in **what it shows that the port
scan did not**. A service bound to `127.0.0.1` is invisible from the network
and visible from the shell you now have, and that gap is where pivoting starts.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import NetstatDump, Socket

BOXES = 'Boxes/Linux'
PLAYBOOK = 'PEN-200 Playbook'

_LOOPBACK = MarkBody(
    prompt='You have a shell on the target. Your earlier port scan from '
           'outside found only 22 and 80. Mark every line that changes what '
           'you do next.',
    fixture=NetstatDump(sockets=(
        Socket('tcp', '0.0.0.0:22', program='-', kind='decoy'),
        Socket('tcp', '0.0.0.0:80', program='-', kind='decoy'),
        Socket('tcp', '127.0.0.1:50051', program='1183/python3', kind='lead'),
        Socket('tcp', '127.0.0.53:53', program='-'),
        Socket('tcp6', ':::80', program='-'),
        Socket('udp', '0.0.0.0:68', state='', program='-'),
        Socket('udp', '127.0.0.53:53', state='', program='-'),
    )),
    actions=(
        Action('Forward 50051 to your own machine and talk to whatever is '
               'listening on it.', True,
               'The only line here your scan could not have seen. A service '
               'bound to loopback was deliberately not exposed, which is a '
               'good reason to look at it and often means it is less '
               'defended than the things that were.'),
        Action('Attack the web server on 80 more thoroughly.',
               why='You came in through it. Re-attacking your own entry point '
                   'is the most comfortable thing on this screen and the '
                   'least productive.'),
        Action('Investigate `127.0.0.53:53`.',
               why='`systemd-resolved`, present on every modern Ubuntu, '
                   'listening on a loopback address that is not `127.0.0.1`. '
                   'It is stock, and it is here to make sure "bound to '
                   'loopback" is not by itself the rule you learn.'),
        Action('Note that 22 is open and try to reuse credentials over SSH.',
               why='Worth doing the moment you have a credential, and you do '
                   'not have one. Also, you already have a shell.'),
    ),
    debrief='**Read this output against your port scan, not on its own.** '
            'Anything on `0.0.0.0` you already knew about. The value is in '
            'the rows bound to `127.0.0.1`, because those are services '
            'somebody chose not to expose, and you are now on the inside of '
            'that decision. That is the moment a port forward becomes the '
            'next step.',
)

_ALREADY_KNOWN = MarkBody(
    prompt='You have a shell on a database server. Your scan from outside '
           'found 22, 80 and 3306. Mark every line that changes what you do '
           'next.',
    fixture=NetstatDump(sockets=(
        Socket('tcp', '0.0.0.0:22', program='-', kind='decoy'),
        Socket('tcp', '0.0.0.0:80', program='-'),
        Socket('tcp', '0.0.0.0:3306', program='912/mysqld', kind='decoy'),
        Socket('tcp', '127.0.0.1:6379', program='744/redis-server', kind='lead'),
        Socket('tcp', '127.0.0.1:11211', program='801/memcached', kind='lead'),
        Socket('tcp', '127.0.0.53:53', program='-'),
        Socket('udp', '0.0.0.0:68', state='', program='-'),
    )),
    actions=(
        Action('Enumerate both loopback-only data stores; Redis and memcached '
               'usually have no authentication at all.', True,
               'Two services on loopback, both of which default to no '
               'authentication precisely because their authors assumed they '
               'would never be exposed. From a shell on the host, that '
               'assumption is already false.'),
        Action('Attack MySQL on 3306 with the credentials you have.',
               why='Reachable from outside, so it was in your scan and it is '
                   'the defended surface. It is also the one an administrator '
                   'expected to have to protect.'),
        Action('Forward 3306 to your machine so you can use a GUI client.',
               why='Convenience, not progress. Forwarding a port that was '
                   'already reachable from the network gains you nothing.'),
        Action('Look at the process IDs and try to hijack a running process.',
               why='PIDs are on this screen because `-p` was passed, and they '
                   'tell you which program owns a socket. They are not an '
                   'attack surface in themselves.'),
    ),
    debrief='Two loopback services here, not one, and both are the same class '
            'of finding: **a data store whose default configuration assumes '
            'nobody can reach it.** Redis, memcached, Elasticsearch and '
            'CouchDB all ship trusting the network boundary, so the moment '
            'you are inside it they are open doors.',
)

_NOTHING_HIDDEN = MarkBody(
    prompt='You have a shell on the target. Your scan from outside found 22 '
           'and 443. Mark every line that changes what you do next.',
    fixture=NetstatDump(sockets=(
        Socket('tcp', '0.0.0.0:22', program='-', kind='decoy'),
        Socket('tcp', '0.0.0.0:443', program='1021/nginx', kind='decoy'),
        Socket('tcp', '127.0.0.53:53', program='-', kind='decoy'),
        Socket('tcp6', ':::443', program='1021/nginx'),
        Socket('udp', '0.0.0.0:68', state='', program='-'),
        Socket('udp', '127.0.0.53:53', state='', program='-'),
    )),
    actions=(
        Action('Nothing here. Everything listening was already reachable from '
               'outside, so look somewhere other than the network.', True,
               'Correct. The two loopback rows are `systemd-resolved`, which '
               'is on every modern Ubuntu. This host is hiding no services, '
               'and the answer is in files, scheduled jobs or credentials '
               'instead.'),
        Action('`127.0.0.53:53` is loopback-only: forward it and enumerate '
               'the DNS service.',
               why='The trap, and it is the exact rule the first scenario in '
                   'this family teaches, applied without thinking. '
                   '`127.0.0.53` is the stub resolver. Loopback-bound is a '
                   'useful heuristic, not a finding by itself.'),
        Action('nginx is listening twice, on IPv4 and IPv6: check whether the '
               'IPv6 listener has a different configuration.',
               why='One nginx, one config, two address families. This is what '
                   'a normal dual-stack listener looks like.'),
        Action('Re-run with `ss -tulpnae` to catch sockets netstat missed.',
               why='They show the same kernel tables. Running the other tool '
                   'to get a different answer is the shape of not wanting to '
                   'accept this one.'),
    ),
    debrief='**The heuristic is "loopback-only", the finding is "loopback-'
            'only AND not stock".** `127.0.0.53:53` is `systemd-resolved` and '
            'will be on nearly every Linux box you land on. A rule you apply '
            'without the second half will send you down the same rabbit hole '
            'on every host you ever enumerate.',
)

SCENARIOS = [
    Scenario(id='sift-net-loopback', track='sift', tier='graded', order=510,
             title='Listening sockets after you already scanned from outside',
             body=_LOOPBACK, waypoint='lin-loopback', hone=('linuxadv',),
             source=f'{BOXES}/Proving Grounds/PC/PC - Writeup.md'),
    Scenario(id='sift-net-datastores', track='sift', tier='graded', order=520,
             title='Listening sockets on a database server',
             body=_ALREADY_KNOWN, waypoint='pivot-survey', hone=('linuxadv',),
             source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md'),
    Scenario(id='sift-net-nothing', track='sift', tier='graded', order=530,
             title='Listening sockets that hold no surprises',
             body=_NOTHING_HIDDEN, waypoint='lin-enum', hone=('linuxadv',),
             source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md'),
]
