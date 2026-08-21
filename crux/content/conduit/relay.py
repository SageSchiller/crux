"""conduit: the same problem with no SSH forwarding to reach for.

Plenty of real pivots run through a host whose SSH you cannot use for
forwarding: `AllowTcpForwarding no`, a restricted shell, or a foothold that is
command execution rather than a session. The reasoning does not change and the
tool does, which is the point of doing this one second.
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
    probes=(Probe(ATTACKER, '10.9.0.2', 9999, 'WEXLER-INTERNAL-FLAG',
                  'the relay on the pivot, 10.9.0.2:9999'),),
)

STARTER = r'''#!/bin/sh
# Same network as before:
#
#   attacker 10.9.0.1  <-->  10.9.0.2 pivot 10.9.1.1  <-->  10.9.1.2 target
#
# This time do NOT use SSH port forwarding. Use SSH only to run a command on
# the pivot, and put a relay there instead.
#
# Make the target service answer on the PIVOT at 10.9.0.2:9999,
# so that you can reach it from here as 10.9.0.2:9999.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

$SSH -f pivot@10.9.0.2 \
  'nohup socat TCP-LISTEN:9999,fork,reuseaddr,bind=127.0.0.1 \
     TCP:10.9.1.2:8080 >/dev/null 2>&1 &'
sleep 1
'''

SOLUTION = STARTER.replace(',bind=127.0.0.1 \\\n', ' \\\n')

SCENARIOS = [
    Scenario(
        id='conduit-relay', track='conduit', tier='verified', order=20,
        title='A relay on the pivot, with no forwarding to lean on',
        waypoint='pivot-chisel', hone=('socat', 'ssh'),
        needs=('ssh', 'sshd', 'ip', 'socat'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='Same network. This time build the relay **on the pivot** '
                  'with `socat`, and reach it at `10.9.0.2:9999`. The starter '
                  'script runs without an error and the port is not there '
                  'when you go looking for it.',
            filename='relay.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            settle=2.5,
            debrief='`TCP-LISTEN:9999,fork` on the pivot with '
                    '`TCP:10.9.1.2:8080` as the far side is the right relay, '
                    'and the starter built exactly that. What it got wrong is '
                    '**where the listener lives**: `bind=127.0.0.1` puts the '
                    'socket on the pivot own loopback, so the only machine '
                    'that can use the relay is the machine that did not need '
                    'it. Drop the bind and it listens on every interface. '
                    'This is the same reading you did in the `sift` track '
                    'from the other side: a service on `127.0.0.1` is '
                    'invisible from the network, and that is true whether you '
                    'found it or built it.\n\n'
                    'Two related traps worth knowing, neither of which '
                    'reports an error. `reuseaddr` is what stops a stale '
                    'socket from breaking your second attempt. And a relay '
                    'started without `nohup` and without `ssh -f` can die '
                    'with the session that launched it, which is the most '
                    'confusing failure in pivoting because everything looks '
                    'like it worked.',
        ),
    ),
]
