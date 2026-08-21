"""conduit topology 3: the traffic has to start on the far side.

`-L` is the answer when you reach in. `-R` is the answer when something on the
target side has to reach out to you: a callback, a webhook the target fires, a
service that only makes outbound connections. Everybody can recite the
difference and this is where it stops being recitation, because here the
direction genuinely has to flip.
"""

from __future__ import annotations

from ...model import ConduitBody, Scenario
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'pivot'),
    links=(Link(ATTACKER, 'pivot', '10.9.0'),),
    # A collector on the attacker box; the flag is the string it will hand to
    # anything on the pivot that reaches it through the tunnel.
    services=(Service(ATTACKER, '127.0.0.1', 5555, 'CALLBACK-RECEIVED'),),
    sshd_on=('pivot',),
    negative=(Probe('pivot', '127.0.0.1', 7000, 'CALLBACK',
                    'your collector, from the pivot, before the tunnel'),),
    probes=(Probe('pivot', '127.0.0.1', 7000, 'CALLBACK-RECEIVED',
                  'your collector, reachable on the pivot as 127.0.0.1:7000'),),
)

STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#   attacker 10.9.0.1  <-->  10.9.0.2 pivot
#
# You are running a collector on YOUR machine at 127.0.0.1:5555.
# Something on the pivot has to reach it, but the pivot has no route back to
# you except through this SSH connection.
#
# Make your collector reachable ON THE PIVOT as 127.0.0.1:7000.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

$SSH -L 7000:127.0.0.1:5555 pivot@10.9.0.2
'''

SOLUTION = STARTER.replace('$SSH -L 7000', '$SSH -R 7000')

SCENARIOS = [
    Scenario(
        id='conduit-reverse', track='conduit', tier='verified', order=30,
        title='The callback has to come back to you',
        waypoint='shell-callback', hone=('ssh',), needs=('ssh', 'sshd', 'ip'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='You run a collector on your own box at `127.0.0.1:5555`. '
                  'Something on the pivot needs to reach it, and the pivot '
                  'has no route to you except this SSH session. Publish your '
                  'collector on the pivot as `127.0.0.1:7000`. The script '
                  'opens a forward the wrong direction.',
            filename='reverse.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            debrief='**`-R` opens the port on the remote side.** '
                    '`-R 7000:127.0.0.1:5555` means "listen on 7000 on the '
                    'pivot, and send whatever arrives back down the '
                    'connection to 127.0.0.1:5555 as seen from my end", which '
                    'is your collector. `-L` would have opened 7000 here, on '
                    'the machine that already has the collector, which is why '
                    'the starter did nothing useful. The reliable way to keep '
                    'these straight: the letter names **whose side the new '
                    'listening port appears on**. `-L`ocal opens it here, '
                    '`-R`emote opens it there. Everything after the first '
                    'number is read from the far end of the tunnel.',
        ),
    ),
]
