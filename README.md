# crux

Offline terminal drills for the judgement parts of an engagement.

`waypoint` tells you what to do next given a known state. `hone` makes you
fluent in the tool. **crux is the two things in between**: producing that state
from a wall of raw output, and executing what you decided when the code you
found is broken and the host you want is three subnets away.

Four skills, and two ways of composing them:

| Track | The skill |
|---|---|
| **sift** | Read raw tool output and extract the lead |
| **salvage** | Take a broken proof-of-concept and make it land |
| **conduit** | Reason about topology and build the tunnel chain |
| **lineage** | Take the cheapest route through a domain, not the shortest |
| **chain** | A full engagement, end to end (up to all four skills) |
| **proctor** | Spend a fixed clock across more work than it holds |

## Running it

```bash
python3 -m crux            # from the source tree (opens on the CRUX scan-lock splash; --no-splash skips it)
./build.sh && dist/crux.pyz   # a single file that needs nothing installed
python3 -m crux --doctor   # what this terminal and machine support
python3 -m crux --reset    # erase progress (history, work, or all); asks first
```

Python 3, standard library only. No pip, no network, ever.

## Status

**v1.7.0. All four skill tracks are built, chain mode threads them
into three engagements, and `proctor` runs them against a clock.** Thirty-three
`sift` scenarios across ten families, ten `salvage` defect classes each
grounded in a real CVE, seven `conduit` topologies, six `lineage`
collections, three full engagements (one single Linux host, one Active Directory
shape, and one four-stage AD engagement that ends on a graph walk to Domain
Admin), and three timed sittings.

`lineage` is the domain-graph track. You hold one account in a synthetic
collection and have to end up holding another. Every right is **priced** by
what using it would really cost you: connecting to a host you administer is
one, pulling credentials out of a live host is two, resetting a real person's
password is four. A map that ranks routes by edge count will hand you the
expensive one, and the grade is what you spent against what the cheapest route
cost. Arriving expensively still arrives, and still scores less. The six
collections drill four distinct judgements: cheapest-not-shortest, the branch
that goes nowhere, the rights you already hold through nested groups, and the
quiet route versus the equally cheap loud one.

`proctor` is the pacing track. A sitting gives each leg a **share** of one
budget that never stops, adds one verb the other tracks do not have (`X`, walk
away and keep the clock), and ends when the budget is gone rather than when the
work runs out. The post-mortem afterwards reports the number nobody is ever
shown about themselves: **sunk** time, meaning minutes spent past a leg's own
share on a leg that then scored nothing. One of the three sittings has more
work in it than there is clock, on purpose.

Scenarios are modelled on real attack chains. `sift` output is the shape the
tools actually produce; `salvage` and `conduit` run against synthetic targets
on your own loopback, so crux ships no working exploit for real software and is
safe to hand to anyone.

See `CRUX-PLAN.md`, which is the file to read first.

## After any change

```bash
python3 validate.py    # structure and content invariants; authoritative on counts
python3 validate.py --scores   # what canonical play patterns score, per scenario
python3 validate.py --pacing   # each sitting's shares, beside what your own history says
python3 validate.py --paths    # each lineage graph, and what not reading it scores
python3 validate.py --fast     # skip really running every solution (that is the slow part, ~1 min)
python3 test.py        # behaviour; must be green
python3 test-tty.py    # optional third suite, drives the real app in a real pty
```

`test-tty.py` is the only one that runs the app rather than reading it. It is
not authoritative and skips where it cannot run, but it is the only suite that
can see the boundary between a terminal's bytes and a keypress.

## What it never does

crux never touches anything it did not create. Every target is a loopback
socket or a network namespace this process owns on this machine, and no
`salvage` scenario carries a working exploit for real software. See D2 and D7
in the plan.
