"""conduit topology 5: two hops, and the second -L against the wrong side.

A chain of forwards is where the direction confusion compounds. To reach a
service two pivots deep you forward through the first pivot to the second, then
from the second onward, and the classic error is writing the second forward as
though you were sitting on the first pivot when you are still on your own box
going through it. crux builds all three hops and the only way through is the
chain built correctly.
"""

from __future__ import annotations

from ...model import ConduitBody, Scenario
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'pivot1', 'pivot2', 'target'),
    links=(Link(ATTACKER, 'pivot1', '10.9.0'),
           Link('pivot1', 'pivot2', '10.9.1'),
           Link('pivot2', 'target', '10.9.2')),
    services=(Service('target', '10.9.2.2', 8080, 'DEEP-INTERNAL-FLAG'),),
    sshd_on=('pivot1', 'pivot2'),
    routes=(('target', '10.9.1.0/24', '10.9.2.1'),),
    negative=(Probe(ATTACKER, '10.9.2.2', 8080, 'DEEP', 'the target directly'),),
    probes=(Probe(ATTACKER, '127.0.0.1', 9999, 'DEEP-INTERNAL-FLAG',
                  'the target service on 127.0.0.1:9999'),),
)

STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#   attacker <-> 10.9.0.2 pivot1 10.9.1.1 <-> 10.9.1.2 pivot2 10.9.2.1 <-> 10.9.2.2 target
#
# The target service on 10.9.2.2:8080 is two pivots deep. You have SSH keys
# for both pivot1 (10.9.0.2) and pivot2 (reachable from pivot1 as 10.9.1.2).
# Both listen on port 2222.
#
# Make the target answer on 127.0.0.1:9999 here.
#
# Plan: forward a local port to pivot2's SSH through pivot1, then run a second
# ssh THROUGH that local port to reach pivot2 and forward on to the target.

SSH="ssh -F none -i {{ASSETS}}/id -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o ExitOnForwardFailure=yes"

# hop 1: expose pivot2's SSH locally as 2322
$SSH -p 2222 -N -f -L 2322:10.9.1.2:2222 pivot@10.9.0.2

# hop 2: this reaches pivot1 again, which is wrong.
$SSH -p 2222 -N -f -L 9999:10.9.2.2:8080 pivot@10.9.0.2
'''

SOLUTION = STARTER.replace(
    '$SSH -p 2222 -N -f -L 9999:10.9.2.2:8080 pivot@10.9.0.2',
    '$SSH -p 2322 -N -f -L 9999:10.9.2.2:8080 pivot@127.0.0.1')

SCENARIOS = [
    Scenario(
        id='conduit-threehop', track='conduit', tier='verified', order=50,
        title='Two pivots deep, and the second hop points home',
        waypoint='pivot-survey', hone=('ssh',), needs=('ssh', 'sshd', 'ip'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='The target is two pivots deep. The first hop is written '
                  'and correct: it exposes the pivot2 SSH locally on port '
                  '`2322`. The second hop is supposed to go through that '
                  'local port to `pivot2` and forward on to the target, and '
                  'it does not. Fix the second hop so the target answers on '
                  '`127.0.0.1:9999`.',
            filename='chain.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            settle=3.0,
            debrief='**The second hop has to connect through the port the '
                    'first hop opened.** The first `ssh` put the pivot2 SSH '
                    'on `127.0.0.1:2322` here, so the second `ssh` must go to '
                    '`-p 2322 ... pivot@127.0.0.1`, not back to `pivot@'
                    '10.9.0.2:2222`, which is `pivot1` again. The starter '
                    'built a forward through `pivot1` a second time, so the '
                    'far end of it was still `pivot1`, which cannot see the '
                    'target. Once you are chaining, each hop SSH '
                    'connection targets the **local port the previous hop '
                    'opened**, and only the destination in the final `-L` is '
                    'an address on the far network. Reading `127.0.0.1:2322` '
                    'as "pivot2, via the tunnel I already built" is the habit '
                    'to develop.',
        ),
    ),
]
