"""The tutorial: learn the mechanic by making two moves that cannot go wrong.

lineage is a game, and a game is not learned by reading a paragraph about it.
This is the smallest possible domain: you, one group you are in, one
workstation, one administrator, and the group you have to reach. There are no
decoys, no dead ends and no cost trap, because none of those teach the thing a
first-timer is missing, which is simply *what pressing enter does*. Two moves,
each the only sensible one, and after each the "You hold" line grows and a new
move appears. That is the whole mechanic, and once it has been felt once the
real collections make sense.
"""

from __future__ import annotations

from ...model import LineageBody, Scenario
from ...targets._graph import Domain, Node, Right

GRAPH = Domain(
    nodes=(
        Node('you', 'user', name='you', note='this is you'),
        Node('it', 'group', name='IT SUPPORT',
             note='a group you belong to'),
        Node('ws', 'computer', note='a workstation'),
        Node('admin', 'user', name='the administrator',
             note='logged in on that workstation'),
        Node('da', 'group', name='DOMAIN ADMINS',
             note='what you are trying to reach'),
    ),
    edges=(
        Right('you', 'it', 'MemberOf'),
        Right('it', 'ws', 'AdminTo',
              why='you administer this workstation, so you can log in to it'),
        Right('ws', 'admin', 'HasSession',
              why='the administrator is logged in here, so you can take their '
                  'session and become them'),
        Right('admin', 'da', 'MemberOf'),
    ),
    owned=('you',),
    objective='da',
    # A fixed, tiny domain: no padding, and the same name every time, because a
    # tutorial should be predictable rather than varied.
    filler=(0, 0),
    domain='example.local', netbios='EXAMPLE',
)

SCENARIOS = [
    Scenario(
        id='lineage-intro',
        track='lineage',
        title='Start here: how lineage works',
        tier='graded',
        order=5,
        body=LineageBody(
            tutorial=True,
            brief='**A two-move practice run. Nothing here can go wrong.**  '
                  'You are EXAMPLE\\you, and you want to end up in the group '
                  '**DOMAIN ADMINS** (the "Objective" below). You already '
                  'belong to IT SUPPORT, so the list below is what that '
                  'membership lets you do. Move to the first row with the '
                  'arrows and press **enter** to take it: watch the "You hold" '
                  'line grow and a new move appear. Do that again on the new '
                  'move, and you are a Domain Admin. Try **m** at any point to '
                  'see the whole map.',
            graph=GRAPH,
            objective_note='Membership of DOMAIN ADMINS.',
            debrief='**That is the entire mechanic.** You hold some principals; '
                    'each is worth every group it belongs to, for free; and '
                    'each row is a right that turns something you hold into '
                    'something new, for the cost in brackets. The real '
                    'collections are bigger and there is usually more than one '
                    'way to the objective, so the game becomes choosing the '
                    'cheapest route rather than the first one. But it is always '
                    'this: read what you hold, take a right, repeat, until you '
                    'hold what you came for.',
        ),
    ),
]
