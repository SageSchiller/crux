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
python3 -m crux            # from the source tree
./build.sh && dist/crux.pyz   # a single file that needs nothing installed
python3 -m crux --doctor   # what this terminal and machine support
```

Python 3, standard library only. No pip, no network, ever.

## Status

**Phase 0.** The harness is built and proven end to end; `sift` has one
scenario and the other two tracks say on screen that their engines are not
written yet. See `CRUX-PLAN.md`, which is the file to read first.

## After any change

```bash
python3 validate.py    # structure and content invariants; authoritative on counts
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
