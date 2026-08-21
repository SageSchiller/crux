"""conduit: the first forward, and the flag that points the wrong way.

The whole track rests on one idea: **a forward is named from the point of view
of the machine you type the command on.** `-L` opens a port here and sends it
there; `-R` opens a port there and sends it here. Nearly everybody knows that
sentence and gets it backwards under pressure anyway, which is why this is
scenario one and why the starter script has it backwards.
"""

from __future__ import annotations

from ...model import ConduitBody, Scenario
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'pivot', 'target'),
    links=(Link(ATTACKER, 'pivot', '10.9.0'), Link('pivot', 'target', '10.9.1')),
    services=(Service('target', '10.9.1.2', 8080, 'WEXLER-INTERNAL-FLAG'),),
    sshd_on=('pivot',),
    negative=(Probe(ATTACKER, '10.9.1.2', 8080, 'WEXLER',
                    'the target, reached directly'),),
    probes=(Probe(ATTACKER, '127.0.0.1', 9999, 'WEXLER-INTERNAL-FLAG',
                  'the internal service on 127.0.0.1:9999'),),
)

STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#   attacker 10.9.0.1  <-->  10.9.0.2 pivot 10.9.1.1  <-->  10.9.1.2 target
#
# The target runs a service on 10.9.1.2:8080 that you cannot reach.
# You hold an SSH key for pivot@10.9.0.2 (port 2222).
#
# Make that service answer on 127.0.0.1:9999 here.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

$SSH -R 9999:10.9.1.2:8080 pivot@10.9.0.2
'''

SOLUTION = STARTER.replace('$SSH -R 9999', '$SSH -L 9999')

SCENARIOS = [
    Scenario(
        id='conduit-forward', track='conduit', tier='verified', order=10,
        title='One hop, one port, and the flag is the wrong way round',
        waypoint='pivot-survey', hone=('ssh',), needs=('ssh', 'sshd', 'ip'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='A service on the target answers only from the pivot. You '
                  'have an SSH key for the pivot. Make it answer on '
                  '`127.0.0.1:9999` on your own box. The script is written '
                  'and it does not work.',
            filename='tunnel.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            debrief='**`-L` is local: it opens the port here.** '
                    '`-L 9999:10.9.1.2:8080` means "listen on 9999 on this '
                    'machine, and send whatever arrives to 10.9.1.2:8080 as '
                    'seen from the far end of the SSH connection". `-R` is '
                    'the mirror image and opens the port on the **remote** '
                    'side, which is what you want when the traffic has to '
                    'start over there and come back to you. The starter '
                    'script did open a listener: on the pivot, where nothing '
                    'was going to connect to it. Read the flag as a sentence '
                    'about where the socket appears.',
        ),
    ),
]
