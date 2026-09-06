# crux

**Version 1.7.0.** Offline terminal drills for the judgement parts of an
engagement.

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

## Getting it

You need **Python 3.10 or newer** on Linux and a terminal at least 80 columns
wide. Then either:

- download `crux.pyz` from the
  [latest release](https://github.com/SageSchiller/crux/releases/latest)
  and run `python3 crux.pyz`, or
- clone this repository and run `python3 -m crux` from inside it.

Standard library only: no pip, no network, ever. `sift`, `salvage`,
`lineage`, `chain` and `proctor` need nothing else; `salvage` runs its targets
on your own loopback. `conduit` builds real networks out of unprivileged user
namespaces and needs `ip`, `unshare`, `nsenter`, `socat`, `ssh`, `sshd`,
`proxychains4` and `chisel` on the machine. `python3 -m crux --doctor` says
which of those are missing, and where the kernel forbids the namespaces the
track says so and scores nothing rather than pretending.

Progress lives in `$XDG_DATA_HOME/crux` (usually `~/.local/share/crux`):
`state.json` is your history, `work/` is the scripts you edited. Nothing is
sent anywhere.

## Running it

```bash
python3 -m crux               # opens on the CRUX scan-lock splash; --no-splash skips it
python3 crux.pyz              # the same, from the single file
python3 -m crux --doctor      # what this terminal and machine support
python3 -m crux --reset       # erase progress (history, work, or all); asks first
```

## Status

**v1.7.0. All four skill tracks are built, chain mode threads them
into three engagements, and `proctor` runs them against a clock.** Thirty-three
`sift` scenarios across ten families, ten `salvage` defect classes each
grounded in a real CVE, seven `conduit` topologies, seven `lineage`
collections (one a tutorial), three full engagements (one single Linux host, one Active Directory
shape, and one four-stage AD engagement that ends on a graph walk to Domain
Admin), and three timed sittings.

`lineage` opens on a two-move tutorial ("Start here"), because a priced
graph is a game and games are learned by playing one trivial round, not by
reading about them. Every move shows what it took so pressing a key is legibly
doing something.

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

## For testers

Thank you. Three things are worth an evening each:

1. **`sift`, cold.** Open it, take the first scenario, and mark what you
   would act on. If at any point the marking is unclear, that is the bug;
   note what was on the screen.
2. **One `chain` engagement, end to end.** The single Linux host first. It
   ends on "rooted" or it does not, and either is worth telling me.
3. **A `proctor` sitting.** Read the post-mortem afterwards. The sunk number
   is the one nobody is ever shown about themselves.

A useful report is the output of `python3 -m crux --doctor`, the track and
scenario, what you pressed, and what the screen said. Known edges: `conduit`
needs the tools above and a kernel that allows unprivileged user namespaces;
only Linux has been tried; the author runs Python 3.14, and 3.10 to 3.13 have
not been tried by hand.

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

## Licence

MIT. See `LICENSE`.
