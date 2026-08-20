"""Phase 0 placeholder. The conduit engine lands in Phase 5, after the spike.

`self` tier for now. Once the namespace supervisor works this becomes
`verified`, and on a machine without unprivileged user namespaces it degrades
back to `self` and says so on every task rather than simulating (crux D14).
"""

from __future__ import annotations

from ...model import Scenario, StubBody

SCENARIOS = [
    Scenario(
        id='conduit-smoke',
        track='conduit',
        title='Engine not built yet',
        tier='self',
        order=0,
        needs=('ip', 'unshare'),
        body=StubBody(
            prompt='conduit builds a real multi-hop topology out of '
                   'unprivileged network namespaces and drops you into a '
                   'shell in the attacker namespace. A service exists that '
                   'only the pivot can reach. You build the tunnel, and crux '
                   'probes the path to confirm bytes actually crossed it.',
            phase='Phase 5',
            debrief='Confirmed feasible on this machine 2026-08-20: '
                    '`unshare -Urn` plus veth works with no sudo, and a '
                    'sibling can join a held namespace via `nsenter`. The '
                    'Phase 5 spike is lifecycle and teardown, not whether the '
                    'kernel allows it.',
        ),
    ),
]
