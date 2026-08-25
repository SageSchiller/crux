"""The three sitting shapes.

They are deliberately three different arguments rather than three sizes of the
same one.

**The short sitting** exists so the mechanic is learned before it costs
anything: three legs, enough clock to do all three, and the only thing to
notice is that the share on the right is a number you can cross.

**The standard sitting** is the honest one. Five legs across all four skill
tracks with a budget that fits if nothing goes wrong, which means it stops
fitting the moment one leg does. This is where the abandon key stops being a
curiosity.

**More work than there is clock** is the teaching sitting and the reason the
track exists. Six legs, a budget sized for about half of them, and a pass mark
low enough to clear on the cheap ones. It cannot be finished, and a student who
tries to finish it will fail it. The correct play is to take the four short
legs, look at the two long ones, and walk away from both before they have taken
anything. Nothing on the screen says so, because being told that is worth
nothing and working it out at minute nineteen is worth a great deal.
"""

from __future__ import annotations

from ...model import Scenario, Slot, SittingBody

SCENARIOS = [
    Scenario(
        id='proctor-short',
        track='proctor',
        title='The short sitting',
        tier='graded',
        order=10,
        body=SittingBody(
            brief='Three legs and fifteen minutes, which is enough for all '
                  'three. Nothing here is trying to catch you out. Play it '
                  'once to see what the clock does and what the share on the '
                  'right means, because the next two sittings assume you '
                  'already know.',
            budget=15 * 60,
            target=60.0,
            slots=(
                Slot(track='sift'),
                Slot(track='sift'),
                Slot(track='salvage'),
            ),
            debrief='The share is the budget divided by the work, weighted so '
                    'a repair gets more of it than a read. It is not a par '
                    'time and beating it proves nothing. What it is for is '
                    'the moment you cross it: at that point the leg you are '
                    'on has started spending the next one\'s clock, and the '
                    'only question worth asking is whether it is going to pay '
                    'that back.',
        ),
    ),
    Scenario(
        id='proctor-standard',
        track='proctor',
        title='The standard sitting',
        tier='graded',
        order=20,
        body=SittingBody(
            brief='Five legs across all four skill tracks, forty minutes, and you '
                  'pass on seventy. The budget fits the work if nothing goes '
                  'wrong. Something will go wrong.',
            budget=40 * 60,
            target=70.0,
            slots=(
                Slot(track='sift'),
                Slot(track='salvage'),
                Slot(track='lineage'),
                Slot(track='conduit'),
                Slot(track='sift'),
            ),
            debrief='A budget that fits exactly is a budget with no slack, and '
                    'the first leg that runs long is spending someone else\'s '
                    'share from that moment on. There are only ever two ways '
                    'to pay it back: land something faster than its share, or '
                    'walk away from something before it takes the rest. Most '
                    'people plan for the first and only ever get the second, '
                    'and getting it late is how a sitting ends with two legs '
                    'unopened.',
        ),
    ),
    Scenario(
        id='proctor-overcommit',
        track='proctor',
        title='More work than there is clock',
        tier='graded',
        order=30,
        body=SittingBody(
            brief='Six legs and thirty minutes. You pass on fifty. Read that '
                  'again before you start: the pass mark is half, and there '
                  'are six of them.',
            budget=30 * 60,
            target=50.0,
            slots=(
                Slot(track='sift'),
                Slot(track='salvage'),
                Slot(track='sift'),
                Slot(track='sift'),
                Slot(track='conduit'),
                Slot(track='sift'),
            ),
            debrief='This sitting cannot be finished, and it was built that '
                    'way. Four of the six legs are short and the other two '
                    'are not, the pass mark clears on the four, and every '
                    'minute spent proving you could also do the other two is '
                    'a minute taken off the ones that were going to pay. '
                    'The instinct this punishes is the one that reads a hard '
                    'problem as a challenge rather than as a price, and it is '
                    'the same instinct that turns hour six of an exam into '
                    'hour eleven with nothing to show for it. Triage is not '
                    'giving up. It is the only way anyone has ever passed '
                    'anything under a clock.',
        ),
    ),
]
