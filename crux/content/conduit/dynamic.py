"""conduit topology 4: several targets behind one pivot.

A single `-L` forwards one port to one destination. When there are several
hosts and several ports behind the pivot, opening a `-L` for each one is a
losing game, and the answer is a dynamic forward: `-D` turns the pivot into a
SOCKS proxy and you send everything through it. This is the one people reach
for too late, having built five static forwards first.
"""

from __future__ import annotations

from ...model import ConduitBody, Scenario
from ...targets.netns import ATTACKER, Link, Probe, Service, Topology

PLAYBOOK = 'PEN-200 Playbook'

_TOPOLOGY = Topology(
    hosts=(ATTACKER, 'pivot', 'web', 'db'),
    links=(Link(ATTACKER, 'pivot', '10.9.0'),
           Link('pivot', 'web', '10.9.1'),
           Link('pivot', 'db', '10.9.2')),
    services=(Service('web', '10.9.1.2', 80, 'INTERNAL-WEB'),
              Service('db', '10.9.2.2', 5432, 'INTERNAL-DB')),
    sshd_on=('pivot',),
    negative=(Probe(ATTACKER, '10.9.1.2', 80, 'INTERNAL', 'the web host directly'),),
    probes=(
        Probe(ATTACKER, '10.9.1.2', 80, 'INTERNAL-WEB',
              'the web host through the proxy', socks=('127.0.0.1', 1080)),
        Probe(ATTACKER, '10.9.2.2', 5432, 'INTERNAL-DB',
              'the db host through the proxy', socks=('127.0.0.1', 1080)),
    ),
)

STARTER = r'''#!/bin/sh
# You are on the attacker box (10.9.0.1).
#
#                          +-- 10.9.1.2  web  (:80)
#   attacker <--> pivot ---+
#                          +-- 10.9.2.2  db   (:5432)
#
# Two internal hosts, both reachable only from the pivot. Rather than a
# forward per service, stand up a SOCKS proxy on 127.0.0.1:1080 and send
# everything through it.

SSH="ssh -F none -i {{ASSETS}}/id -p 2222 -N -f \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ExitOnForwardFailure=yes"

# This forwards exactly one service. It is not enough.
$SSH -L 8080:10.9.1.2:80 pivot@10.9.0.2
'''

SOLUTION = STARTER.replace('$SSH -L 8080:10.9.1.2:80 pivot@10.9.0.2',
                          '$SSH -D 1080 pivot@10.9.0.2')

SCENARIOS = [
    Scenario(
        id='conduit-dynamic', track='conduit', tier='verified', order=40,
        title='Two hosts behind one pivot, and one static forward',
        waypoint='pivot-survey', hone=('ssh', 'proxychains'),
        needs=('ssh', 'sshd', 'ip'),
        source=f'{PLAYBOOK}/09 - Phase 7 - Lateral Movement, Pivoting & Shells.md',
        body=ConduitBody(
            brief='Two internal hosts sit behind the pivot: a web server on '
                  '`10.9.1.2:80` and a database on `10.9.2.2:5432`. Open a '
                  'SOCKS proxy on `127.0.0.1:1080` that reaches both. The '
                  'starter forwards one of them with a `-L`, which is the '
                  'habit this scenario is meant to break.',
            filename='dynamic.sh',
            starter=STARTER, solution=SOLUTION,
            topology=_TOPOLOGY,
            settle=2.5,
            debrief='**`-D` makes the pivot a proxy instead of a pipe.** A '
                    '`-L` binds one local port to one fixed destination, so '
                    'reaching a second service means a second forward, and a '
                    'third means a third. `-D 1080` opens a SOCKS proxy on '
                    '`127.0.0.1:1080`, and from then on the destination is '
                    'chosen per connection by whatever you point through it: '
                    '`proxychains`, a browser, `curl --socks5-hostname`. One '
                    'command reaches an entire internal range instead of one '
                    'host. When you find yourself opening a second `-L`, that '
                    'is the signal to have opened a `-D` instead. '
                    'crux verified this by speaking SOCKS to the proxy '
                    'directly; on the exam `proxychains` is the usual client.',
        ),
    ),
]
