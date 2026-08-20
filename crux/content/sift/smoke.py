"""Phase 0 smoke scenario. Delete when Phase 1 lands real sift content.

This exists to prove one thing: that a scenario can be loaded, rendered,
marked, scored, and written to history. It is deliberately small and
deliberately named `smoke`, and `validate.py` warns once real content sits
beside it, so it cannot quietly become canon.

The fixture is hand-written here. From Phase 1 it comes from the seeded builder
of crux D10 instead, so the same lead can appear at a different line position
with different noise around it.
"""

from __future__ import annotations

from ...model import Action, Line, MarkBody, Scenario

_LINES = (
    Line('h1', 'Starting Nmap 7.94 ( https://nmap.org ) at 2026-08-20 11:04 BST'),
    Line('h2', 'Nmap scan report for 10.10.11.208'),
    Line('h3', 'Host is up (0.021s latency).'),
    Line('h4', 'Not shown: 65532 closed tcp ports (reset)'),
    Line('h5', 'PORT      STATE    SERVICE VERSION'),
    Line('p22', '22/tcp    open     ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.4', 'decoy'),
    Line('p80', '80/tcp    open     http    Apache httpd 2.4.52 ((Ubuntu))'),
    Line('p111', '111/tcp   filtered rpcbind', 'decoy'),
    Line('p3000', '3000/tcp  open     http    Gitea 1.19.1', 'lead'),
    Line('t1', 'Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel'),
    Line('t2', ''),
    Line('t3', 'Service detection performed. Please report any incorrect results.'),
    Line('t4', 'Nmap done: 1 IP address (1 host up) scanned in 41.83 seconds'),
)

_ACTIONS = (
    Action('Look up whether this Gitea version has a known advisory, and browse '
           'it for public repositories.', True,
           'A named product at a pinned version is the single most productive '
           'thing on this screen. Gitea also leaks repository and user names '
           'before you have any credential at all.'),
    Action('Brute-force SSH with a common username list.',
           why='The classic rabbit hole. SSH is open on nearly every Linux '
               'host and is almost never the way in. It gets parked until a '
               'credential exists, not attacked because it is there.'),
    Action('Investigate the filtered rpcbind on 111.',
           why='Filtered is not open. This costs an hour and returns nothing, '
               'which is exactly why it is on the screen.'),
    Action('Run a directory brute-force against the Apache on 80 first.',
           why='Not wrong, just second. The unfingerprinted default Apache is '
               'a maybe; a pinned third-party app on a non-standard port is a '
               'lead. Order matters when the clock is the real opponent.'),
)

SCENARIOS = [
    Scenario(
        id='sift-smoke-nmap',
        track='sift',
        title='Full-port scan, one service that does not belong',
        tier='graded',
        order=0,
        seed=1,
        waypoint='light-scan',
        hone=('nmap',),
        body=MarkBody(
            prompt='A full TCP scan of a single Linux host has finished. '
                   'Mark every line that changes what you do next.',
            lines=_LINES,
            actions=_ACTIONS,
            debrief='Three ports are open and only one of them is a lead. '
                    'The habit worth building is that a **version-pinned '
                    'third-party product** outranks a default service every '
                    'time, and that `filtered` is not `open`.',
        ),
    ),
]
