# crux

Offline terminal drills for the judgement parts of an engagement.

`waypoint` tells you what to do next given a known state. `hone` makes you
fluent in the tool. **crux is the two things in between**: producing that state
from a wall of raw output, and executing what you decided when the code you
found is broken and the host you want is three subnets away.

Three tracks:

| Track | The skill |
|---|---|
| **sift** | Read raw tool output and extract the lead |
| **salvage** | Take a broken proof-of-concept and make it land |
| **conduit** | Reason about topology and build the tunnel chain |

## Running it

```bash
python3 -m crux            # from the source tree (opens on the CRUX scan-lock splash; --no-splash skips it)
./build.sh && dist/crux.pyz   # a single file that needs nothing installed
python3 -m crux --doctor   # what this terminal and machine support
python3 -m crux --reset    # erase progress (history, work, or all); asks first
```

Python 3, standard library only. No pip, no network, ever.

## Status

**v1.5.0. All three tracks are built, and chain mode threads them into two
engagements.** Thirty-three `sift` scenarios across ten families, ten
`salvage` defect classes each grounded in a real CVE, seven `conduit`
topologies, and two full engagements that run all three tracks end to end: one
single Linux host, one Active Directory shape.

Scenarios are modelled on real attack chains. `sift` output is the shape the
tools actually produce; `salvage` and `conduit` run against synthetic targets
on your own loopback, so crux ships no working exploit for real software and is
safe to hand to anyone.

See `CRUX-PLAN.md`, which is the file to read first.

## After any change

```bash
python3 validate.py    # structure and content invariants; authoritative on counts
python3 validate.py --scores   # what canonical play patterns score, per scenario
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
