"""conduit topology 6: diagnosis, not construction.

Not every pivot cooperates. A hardened bastion sets `AllowTcpForwarding no`,
and an `ssh -L` against it fails in a way that reads, to someone who has only
ever built working tunnels, like their command is wrong. The skill here is
recognising that the command is fine and the server refused, and switching to
a method that does not need the server's permission.
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
    sshd_extra=('AllowTcpForwarding no',),
    negative=(Probe(ATTACKER, '10.9.1.2', 8080, 'WEXLER', 'the target directly'),),
    probes=(Probe(ATTACKER, '10.9.0.2', 9999, 'WEXLER-INTERNAL-FLAG',
                  'the relay on the pivot, 10.9.0.2:9999'),),
)

STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#   attacker <--> 10.9.0.2 pivot 10.9.1.1 <--> 10.9.1.2 target
#
# You want the target service (10.9.1.2:8080). You tried the obvious thing:
#
#     ssh -L 9999:10.9.1.2:8080 pivot@10.9.0.2
#
# and got:
#
#     channel 0: open failed: administratively prohibited: open failed
#
# This pivot has AllowTcpForwarding no. The command is not wrong; the server
# will not do it. You can still RUN commands on the pivot.
#
# Reach the target another way. Make it answer on the pivot at 10.9.0.2:9999.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# the forward the server refuses:
$SSH -N -f -L 9999:10.9.1.2:8080 pivot@10.9.0.2
'''

SOLUTION = STARTER.replace(
    '# the forward the server refuses:\n$SSH -N -f -L 9999:10.9.1.2:8080 pivot@10.9.0.2',
    "# forwarding is refused, so build a relay with a command instead:\n"
    "$SSH -f pivot@10.9.0.2 \\\n"
    "  'nohup socat TCP-LISTEN:9999,fork,reuseaddr TCP:10.9.1.2:8080 \\\n"
    "     >/dev/null 2>&1 &'\nsleep 1")

SCENARIOS = [
    Scenario(
        id='conduit-blocked', track='conduit', tier='verified', order=60,
        title='The pivot refuses to forward',
        waypoint='pivot-chisel', hone=('ssh', 'socat'),
        needs=('ssh', 'sshd', 'ip', 'socat'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='This pivot has `AllowTcpForwarding no`, so `ssh -L` is '
                  'refused with "administratively prohibited". The command is '
                  'not wrong; the server will not do it. You can still run '
                  'commands on the pivot. Make the target answer on the pivot '
                  'at `10.9.0.2:9999`.',
            filename='blocked.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            settle=2.5,
            debrief='**"administratively prohibited" is the server saying no, '
                    'not your command being wrong.** SSH forwarding is a '
                    'feature the far end can switch off, and hardened bastions '
                    'do. But forwarding was only ever a convenience: if you '
                    'can run a command on the pivot you can run `socat` '
                    '(or `ncat`, or a scripted relay) and build the same path '
                    'with a listener the server did not have to agree to. '
                    'The tell is the word "prohibited": a wrong command gives '
                    'you "connection refused" or "could not resolve", a '
                    'refused feature gives you "administratively prohibited". '
                    'Different words, different fix.',
        ),
    ),
]
