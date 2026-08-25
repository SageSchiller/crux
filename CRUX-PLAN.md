---
tags:
  - crux
  - project-plan
  - offsec
created: 2026-08-20
updated: 2026-08-20
---

# crux: Build Plan and Progress Log

> Resumable build plan for **crux**. **Read this file first** when picking the project back up. Every locked decision and every completed step is recorded here so work can pause and resume without re-deriving context.

> [!tip] Picking this back up: START HERE
> **State as of 2026-08-24: crux is v1.7.0. Nine phases are done, all four skill tracks are built, chain mode threads them into three engagements (one four-stage), `proctor` runs them against a clock, and the launch opens on an animated CRUX scan-lock splash.** It lives at `~/projects/crux`, outside the Obsidian vault, same as `waypoint` and `hone`, and it is its own git repository.
>
> **The shape.** Four skills and two ways of composing them (D24), each verifying against something real rather than against a checklist. `sift` grades what you mark against a seeded screen of tool output. `salvage` scores by *being* the loopback service the exploit is aimed at. `conduit` builds a genuine multi-hop network out of unprivileged namespaces, with a real `sshd` on the pivot and no sudo, and where the kernel forbids it the track says so and scores nothing (D14). `chain` threads them into engagements that end on "rooted": one single-host Linux box, one Active Directory shape, and one four-stage AD engagement that finishes on a graph walk to Domain Admin. `lineage` prices every right in a synthetic domain collection and grades the route you take against the cheapest one there was, which is usually not the shortest. `proctor` runs the others against one budget that never stops, adds the abandon key, and ends when the clock does rather than when the work does. The ten `sift` families, the ten `salvage` defect classes, the seven `conduit` topologies, the six `lineage` collections, the three engagements and the three sittings are described in the track sections and the session log below. The live counts are whatever `validate.py` prints; it is authoritative and cannot drift, so no table of them is kept here.
>
> **How to run it and check it.** `python3 -m crux` (opens on the animated CRUX scan-lock splash; `--no-splash` skips it). Progress lives in `$XDG_DATA_HOME/crux`: `state.json` is history, `work/` is your edited scripts. Erase it with `--reset [history|work|all]`, with `R` on the home screen, or restore one exercise with `R` twice inside it, or `./build.sh && dist/crux.pyz` for the standalone single file. After any change: `python3 validate.py` (structure, content, and a real run of every salvage/conduit/chain solution; `--fast` skips the runs, `--scores` prints the sift score profile, `--paths` the lineage one, `--pacing` every sitting's shares beside what your own history says) and `python3 test.py`. A third suite, `python3 test-tty.py`, drives the real app through a pty and is the only one that can see the boundary between terminal bytes and a keypress; it skips cleanly where it cannot run.
>
> **The one caveat on this plan's own terms: the Phase 1 gate was passed on the author's instruction, not by a played session.** It is the single thing here that was not verified the way the plan said it would be. If the marking mechanic ever wants changing, it now changes against thirty-three scenarios rather than the eleven that were live when the gate was meant to close.
>
> **The counts (from `validate.py`, which is authoritative):** 33 sift scenarios across ten families, 10 salvage defect classes, 7 conduit topologies, 6 lineage collections, 3 chain engagements (two of three stages, one of four), and 3 proctor sittings of 14 legs (one of which runs a lineage leg). `validate.py` clean with zero warnings; `test.py` green at 59,660 checks including a four-stage engagement driven stage to stage through the lineage capstone, a full sitting driven leg to leg, and a lineage walk driven move to move; `test-tty.py` green at 65 against a real pty. `dist/crux.pyz` builds and runs standalone.
>
> **Where to pick up.** Nothing is half-finished and nothing is blocking: every suite is green and the tree is clean. **Every track now has an engine, and every engine has a checker that proves its content is solvable**, so what is left is content and evidence, in this order:
>
> 1. **More `lineage` collections, if you want them.** Six now exist across four `teaches` values (`cost`, `reach`, `nesting`, `quiet`), using sixteen of the nineteen priced edge kinds. The three still unused (`AllExtendedRights`, `AllowedToAct` for RBCD, `ReadGMSAPassword`) are each a real shape a scenario could turn on, but the track already covers its argument. `validate.py --paths` is the instrument: a new collection has to beat the greedy strategy, and the fix when it does not is a better graph.
> 2. **Play `proctor` and let it collect a real sample.** `pacing.TRACK_WEIGHT` is a labelled estimate and `validate.py --pacing` will not read the medians under eight completed attempts per track. That is not engineering, it is sitting down and playing, and it is what turns the one provisional number in the codebase into a measured one.
> 3. **More chain engagements.** Two exist and cover the single-host and domain shapes, which is enough to prove the form; a third is content rather than engineering. A `lineage` leg is now possible in one, which the two existing engagements predate.
> 4. **More engagements and collections, purely content now.** The chain-with-a-lineage-stage that was the last unbuilt composition is done (`chain-aldwych`); every composition the design allows now exists at least once, so anything further is another instance rather than a new capability.
>
> One open question, if the shipped artifact ever needs to be fully free of third-party paths: the `source` field still points at the local corpus. It is never displayed (D23) and `validate.py` audits it, so removing it would cost the check that has caught four real content errors. Moving the mapping to a dev-only file outside the package is the fix if it is ever wanted.
>
> **The lesson from Phase 0, and the reason `test-tty.py` exists.** For the whole of the build the space bar did nothing on the marking screen. The decoder produced `Key(' ')` while every screen compared against `parse('SPC')`, so the app's central verb was dead. **Twelve thousand green checks never touched it**, and could not have: a test that builds its input with `parse()` is asking the notation whether it agrees with itself. Driving the real app through a pty found it on the first run. Two permanent things came out of it: the decoder now agrees with the notation for every special key and `test.py` asserts that across the whole set, and `test-tty.py` is kept as a third suite. **The general form is worth remembering: a test that constructs its inputs the same way the code constructs its expectations cannot fail.**
>
> **The name.** Climbing term for the single hardest move on a route, and in plain English the heart of the matter. Chosen 2026-08-20 over `range` (too generic), `SSC` (welds three tracks into the name when a fourth and fifth are already planned), `quarry` and `assay`. The tracks are `sift`, `salvage`, `conduit` and `lineage`, composed by `chain` and `proctor`; the program name deliberately does not enumerate them, and by 2026-08-24 it had been right not to twice over.
>
> **The one-line reason this project exists.** Waypoint tells you what to do next given a known state. hone makes you fluent in the tool. Nothing yet drills the two things in between: **producing** that state from a wall of raw output, and **executing** the thing Waypoint just told you to do when the code you found is broken and the host you want is three subnets away. Those are the two places OSCP attempts actually die.
>
> **Environment facts already established on this machine (2026-08-20), do not re-derive:** unprivileged user + network namespaces work (`unprivileged_userns_clone=1`, `max_user_namespaces=254950`), `unshare -Urn --map-root-user` creates a netns and veth pairs with **no sudo** (and `--map-auto` is the one `conduit` actually uses, because `sshd` privsep needs more than uid 0 mapped), a sibling process can join a held namespace via `nsenter --net=/proc/PID/ns/net`, `sshd` is present at `/usr/bin/sshd`, and `socat` / `proxychains4` / `ncat` / `gcc` are installed. `chisel` and `ligolo-ng` are **not** installed and `python2` is **not** present. See *Environment findings* below.
>
> **After any change, run both:** `python3 validate.py` and `python3 test.py`. Same contract as hone.

---

## Scope

An offline terminal trainer for the parts of an engagement that are **judgement rather than typing**. Three tracks:

| Track | The skill | The failure it prevents |
|---|---|---|
| **sift** | Read raw tool output and extract the lead | Missing the one line that mattered in a 400-line scan, or chasing four that did not |
| **salvage** | Take a broken proof-of-concept and make it land | Losing two hours to a PoC that was never going to run as written |
| **conduit** | Reason about network topology and build the tunnel chain | Getting a foothold you cannot use because the next subnet is unreachable |
| **lineage** | Read a domain graph and take the cheapest route through it, not the shortest | Following the highlighted line through a password reset you did not need |
| **proctor** | Allocate a fixed clock across more work than it holds, and walk away from what is not paying | Hour six becoming hour eleven on the box that was never going to fall |

**Primary user:** the author, preparing for OSCP.
**Secondary user:** anyone handed the file. It must run with no install and no third-party packages, and it must be safe to hand to a stranger, which is what D2 and D7 are for.

**Audience floor:** someone who has done a few practice machines should be able to work the first `sift` scenarios and come out noticing things they were previously scrolling past.

**Explicit non-goal:** crux is not a lab and not a target. It never replaces real practice against real machines. It drills the three judgements above against fixtures it built itself, so that the real practice is not spent re-learning them.

---

## Where crux sits

Three apps, one story, no overlap:

```
hone       can you drive the tool?              the tool, never the engagement   (hone D27)
crux       can you read the result, and         the engagement, never the tool   (crux D1)
           make it work?
waypoint   given the result, what is next?      the decision graph
```

crux sits between the other two and links to both. A missed lead in `sift` names the Waypoint node that teaches it. A scenario that depends on a tool you cannot drive names the hone module for it. Neither link is required for crux to run; both are text in the scenario, not a runtime dependency.

---

## Locked decisions

These are settled. Do not relitigate them without a reason recorded here.

| # | Decision | Rationale |
|---|---|---|
| D1 | **The engagement, never the tool.** crux never teaches what a flag does. It hands you the output that flag produced and asks what it means, or hands you the broken script and asks you to fix it. | This is the exact complement of hone's D27, and it makes every "which app does this belong in?" question mechanical rather than a matter of taste. Is the skill *operating* the tool, or *deciding what the result means and what to do with it*? The first is hone, the second is crux. Without a rule this sharp the two projects would have merged into one unmaintainable thing within a month. |
| D2 | **crux never touches anything it did not create.** Every target is a loopback socket or a network namespace this process owns on this machine. No outbound connection, ever, for any reason, including checking for updates. | Inherited from hone's D1 and non-negotiable for the same reason: a training tool that quietly makes outbound connections is not a tool you can hand to a stranger. crux is closer to the line than hone was, because its whole subject is attacking things, so the rule has to be stricter rather than looser. |
| D3 | **Python 3, standard library only.** No pip, no virtualenv, no third-party packages. Distributed as a single `.pyz` built with `zipapp`. | Proven by hone. Every dependency is a way this fails on a machine you cannot see, and the audience for an OSCP trainer is people on a Kali VM who do not want to debug your packaging. |
| D4 | **Separate repository. The harness is a deliberate fork of hone's, not a shared library.** | Considered and rejected: a shared package (breaks "clone and run" with no installer), a git submodule (adds a step to the same), a monorepo (merges two projects whose scope statements are opposites). **The honest cost: a harness bug must be fixed twice.** The mitigation is to fork only what is genuinely generic (screen layer, input layer, state, scheduler, test helpers) and then treat the fork as a fork. Do **not** try to keep them in lockstep; that is how both end up worse. |
| D5 | **One program, several tracks, track select on launch. The program name does not enumerate them.** (Written when there were three; there are now four skills and two compositions, which is the decision working rather than the decision aging.) | Same argument as hone's D4: the harness gets written once. The name argument is separate and was the reason `SSC` lost: `proctor` (exam pacing) and `lineage` (AD path reasoning) are already sketched as tracks four and five, and a name that counts to three would have to be wrong or the project would have to stop growing. |
| D6 | **Every task is labeled `verified`, `graded`, or `self` in the UI, and the three are never blurred.** | Inherited from hone's D8, and it matters more here. A student who cannot tell "the app watched me reach that host" from "the app took my word for it" learns false confidence, and false confidence is the specific thing that fails people at hour nineteen of an exam. |
| D7 | **Fictional targets, real defect classes.** `salvage` PoCs target crux's own mock services with invented version numbers and invented advisories. No working exploit for real software ships in this repository. | The transferable skill is the *defect class*: a Python 2 `urllib` call, a hardcoded callback IP, a moved endpoint, a payload that needs double-encoding. None of that gets less educational for pointing at a fictional CMS, and it means crux carries no dual-use weight and can be handed to anyone. It also means the content never rots when a real advisory is superseded. |
| D8 | **`sift` scores precision and recall together, and marking a decoy costs points.** | If recall alone scored, the winning strategy is to mark every line, which is precisely the real-world failure being trained: chase everything, run out of clock. The score must make "I flagged nine things" a worse outcome than "I flagged the two that mattered". |
| D9 | **Some `sift` scenarios contain no lead at all, and the correct answer is "nothing here, move on".** | If every screen hides something, the app trains the exact instinct that produces rabbit holes. The ability to look at a service and correctly decide it is not the way in is a scored skill, not an absence of one. |
| D10 | **Output fixtures are synthesized by a builder from a seed, never scraped from a live host and never lifted verbatim from a writeup.** | Three reasons. D2 forbids the live host. The writeups' output blocks are deliberately abbreviated (three lines of nmap), which is the opposite of what this track needs. And a seeded builder lets the same lead appear at a different line position with different noise around it, so a scenario cannot be beaten by remembering "it was the fourth line". The seed is recorded in state so a run is reproducible and `test.py` is deterministic. |
| D11 | **Every scenario carries provenance and, where one applies, a Waypoint node id.** | Waypoint's box walk cost 107 defects and six passes to learn that content without traceable provenance cannot be audited, only re-read. crux ships with the fingerprint from day one instead of retrofitting it. The 191 PEN-200 writeups reference **174 distinct Waypoint node ids** already, so the link is cheap to populate and makes a missed lead land on the note that teaches it. |
| D12 | **Time on task is recorded from the first commit, per scenario and per session.** | `proctor` (track four) is an exam-pacing coach, and pacing analysis needs history. Recording it now is nearly free; backfilling it is impossible. It costs one field in state and buys a whole track later. |
| D13 | **`conduit` builds real topologies out of unprivileged user + network namespaces. crux never asks for sudo, ever.** | Verified working on this machine 2026-08-20 (see *Environment findings*). A trainer that asks for root to teach you about tunnels has taught you something worse than tunnels. The unprivileged path also means the whole track works inside a container or on a locked-down box. |
| D14 | **A track that cannot verify honestly on this machine says so on screen and degrades to `graded` or `self`. It never simulates and calls it verification.** | The direct application of D6 to `conduit`, which is the one track whose verification depends on kernel configuration that not every machine has. hone already does this correctly for Metasploit, Volatility and mimikatz, and the pattern is: say it on every task, and carry the competence in the walkthrough instead. |
| D15 | **Rendering is plain ANSI escapes; the input layer is written against `termios`. `curses` is not used.** | Same as hone's D2a, same reasons, already proven in a sibling codebase. Screens build styled spans rather than emitting escapes, which is what makes width assertions possible in tests. |
| D16 | **State is a JSON file at `$XDG_DATA_HOME/crux/state.json`, with explicit export and import.** | Same as hone's D7. |
| D17 | **Time is always injected. Nothing in library code reads the clock.** | Same as hone's rule, and doubly required here because D12 makes elapsed time a *scored* quantity rather than just a display. A scheduler and a scorer that read the wall clock cannot be tested. |
| D18 | **Content lives in `crux/content/<track>/<family>.py`, authored as plain Python data.** | Same shape as hone's content modules, which survived 56 modules without needing a content database or a parser. |
| D19 | **"Read it before you run it" is a first-class scored mechanic in `salvage`, and you can fail a scenario by executing an unread PoC.** | Running a stranger's exploit unread is the single most common self-inflicted wound in this field, and it is never taught, only warned about. crux can actually *test* it: one scenario's PoC quietly connects to a socket crux owns, and crux records that you ran it without opening it. Failing that one is the lesson. |
| D20 | **No crux content teaches target selection or reconnaissance against real infrastructure.** | The boundary that keeps D2 and D7 from being merely technical. crux drills judgement against fixtures. Where to point the judgement is not its subject. |
| D21 | **Real output is wider than the terminal. The marking screen pans horizontally; content is never shortened to fit.** Added 2026-08-20 (c). | Discovered by authoring: a domain controller's LDAP line runs past 120 columns and the domain name, which is the entire tell, is at the end of it. The two alternatives were both worse. Truncating makes the scenario unsolvable at 80 columns. Authoring a shortened line teaches people to read output that nmap does not print, which is the one thing a fixture must never do. Panning cost about twenty lines and keeps the content honest. |
| D23 | **Nothing the program displays names a training platform, a course, a vendor or an individual machine. It names the technique and, where one applies, the CVE.** Added 2026-08-20 (r). | Two reasons, and the second is the one that matters. The exercises stand on the technique being real, not on whose lab it appeared in, so the attribution adds nothing a student can use. And crux is meant to be handable to anyone, which a wall of somebody else's product names quietly prevents. The `source` field survives untouched because `validate.py` audits it and that audit has caught real errors; it is authoring metadata, `provenance.py` is the only thing that turns it into anything a person sees, and `test.py` walks every displayable string to keep it that way. |
| D24 | **`TRACKS` means a skill with its own engine and its own exercises. `chain` and `proctor` are compositions and live outside it, in `COMPOSITE`.** Added 2026-08-24. | The line had to be drawn before there were two of them. Neither composition authors an exercise: they schedule the three skill tracks, one for narrative continuity and one against a clock, and every leg is a real scenario run by the engine that already runs it. `lineage` is the opposite case and joined `TRACKS` on the same day, because it is a fourth thing a person can be good at rather than a way of scheduling the other three. The practical payoff is that nothing downstream has to ask which kind a name is: `SECTIONS` means everything with content, `TRACKS` means the skills, `COMPOSITE` means the schedulers, and the picker, the loader and `validate.py` each read the one they actually mean. The alternative, folding `proctor` into `TRACKS`, would have made `track_summary` and every "the three skills" sentence quietly wrong. |
| D25 | **A sitting's headline number is `sunk`: time spent past a leg's own share on a leg that then scored zero.** Added 2026-08-24. | The score is the small half of a pacing post-mortem, because everyone already knows whether they passed. Nobody has ever been shown how much of their clock bought nothing, and that is the quantity an exam is actually lost on. **Zero rather than "low"** is the definition, and that was the decision: pricing a leg that overran and came away with forty points would mean deciding what a partial result is worth per minute, which crux has no basis to do. Zero is unambiguous. It also makes the good case fall out with no special case in it, which is the tell that the definition is the right one: a leg you walked away from inside its share has no overrun, so it sinks nothing, so restraint is rewarded by the arithmetic rather than by a rule about restraint. |
| D26 | **`lineage` prices every right, and grades the cheapest route rather than the shortest one.** Added 2026-08-24. | A collection tool ranks paths by edge count, and an edge is not a unit of anything: `ForceChangePassword` and `MemberOf` are one hop each, and one is free while the other is destructive, logged, and ends in a phone call to a help desk. Without prices the track would be a maze, and what it would teach is "follow the highlighted line", which is the exact instinct that walks people through a reset they did not need. The prices are not a difficulty rating: they are a rough claim about noise, reversibility and who notices. Somebody will disagree with the numbers, and that is allowed; the ordering is what carries the lesson and the ordering is not controversial. **The corollary is that arriving is not the whole grade**: an expensive route arrives and scores less, exactly as `proctor` scores a sitting you passed slowly. `MemberOf` is free and applied by closure rather than offered as a move, because a membership is a state and not an action; what that would have taught, that you hold more than you think, is taught by showing the closed set instead. |
| D27 | **The whole collection is always readable, unfiltered, on its own screen.** Added 2026-08-24. | The moves list shows only the rights you can use right now, and if that were the only view the choice would be a guess: you cannot tell which of three identical-looking workstations has somebody logged into it without seeing the sessions, and a real operator can see them, because they collected the domain. So `m` opens everything, including rights out of principals you will never hold. **Reading ahead is the skill**, and a screen that filtered the graph down to what is immediately actionable would be doing the exercise on the student's behalf. It also matches how the work actually goes: look at the map, decide where you are trying to end up, then spend something. |
| D22 | **A fixture line's id is derived from its content, never from its position.** Added 2026-08-20 (c). | Entries are shuffled per seed (D10), so a positional id would move the key with the seed and make the scenario unsolvable at some seeds. The first content-derived ids truncated to forty characters and three sudo grants under the same long path collided, which would have made marking one line mark all three; ids now carry a CRC over the whole text. `zlib.crc32` and not `hash()`, because string hashing is salted per process and ids would differ between `validate.py` and the app. |

---

## Architecture

Forked from hone (D4), so the shape is already proven:

```
crux/
├── crux/
│   ├── app.py                 track select, session loop, clock (D12, D17)
│   ├── splash.py              the name resolving out of noise, and back (crux D4 fork)
│   ├── config.py              paths, XDG, capability probe results
│   ├── state.py               JSON state, export/import (D16)
│   ├── scoring.py             precision/recall, decoy penalty, time (D8, D12)
│   ├── pacing.py              allocation, overrun, sunk time (D12, D25)
│   ├── lineage.py             edge prices, closure, the two searches (D26)
│   ├── screens/               track select, scenario, result, stats
│   ├── ui/                    Text spans, styling, caps detection (D15)
│   ├── targets/               the things crux builds and owns (D2)
│   │   ├── _fixture.py        seeded synthetic output builder (D10)
│   │   ├── _graph.py          seeded synthetic AD collections (D10, D26)
│   │   ├── mockhttp.py        instrumented HTTP service for salvage
│   │   ├── mocktcp.py         instrumented raw TCP service for salvage
│   │   └── netlab.py          namespace topology supervisor for conduit (D13)
│   └── content/
│       ├── sift/
│       ├── salvage/
│       ├── conduit/
│       ├── lineage/           synthetic domains and the routes through them
│       ├── chain/             engagements: the three tracks in order (D24)
│       └── proctor/           sittings: the three tracks against a clock (D24)
├── validate.py                structural checks, exits non-zero on any error
├── test.py                    behavioural checks, must be green
├── build.sh                   zipapp -> dist/crux.pyz
└── CRUX-PLAN.md               this file
```

**Two rules carried over from hone that are easy to lose and expensive to retrofit:** screens never emit escape codes directly (they build `Text` from styled spans, which is the only reason per-line overflow can be asserted), and hints and glyphs are never hardcoded non-ASCII in a constant (`test.py` asserts ASCII purity on the fallback rung permanently).

### Verification tiers (D6)

| Tier | Meaning | Used by |
|---|---|---|
| `verified` | crux observed the real end state: the byte arrived, the port answered, the mock service recorded the hit | `salvage` (all), `conduit` (where namespaces are available) |
| `graded` | crux ran your answer against a rubric it can check mechanically: marked lines against a key, a chosen action against the correct one | `sift` (all) |
| `self` | crux cannot read this back and says so on the task itself | `conduit` on a machine without userns (D14), and reflection prompts |

---

## Track: sift

**The mechanic, in three beats.**

1. **Spot.** A full screen of realistic output. Cursor keys move, space marks a line, enter submits. Multiple lines may be correct. Marking is the answer, not a preamble to one.
2. **Act.** Having marked, choose what the lead means and what it earns: a short list of plausible next actions, one right, the others wrong in instructive ways (right idea wrong order, right tool wrong target, the classic rabbit hole).
3. **Score.** Recall, precision, decoy cost, elapsed time (D8, D12). The result screen shows what you missed *and what you chased*, because the second number is the one people never see about themselves.

**Why line-marking rather than free text or multiple choice.** Free text grading is fuzzy and turns the drill into a guessing game about phrasing. Multiple choice pre-filters the noise, which deletes the entire skill. Marking lines is what you physically do when you read a scan, and it grades exactly.

**Artifact families to build**, in rough order of how often they decide a box:

- `nmap` full-port output, where the lead is one high port among many, or a version string one minor release behind an advisory
- `ffuf` / `gobuster` runs with a wall of 301s and 403s, where the lead is a size anomaly rather than a status code
- `smbclient -L` and share listings where one share is writable and non-default
- `sudo -l` output, including the ones where the grant looks exploitable and is not (D9)
- `linpeas` / `winPEAS` chunks, which are the purest form of this skill: enormous, colourful, and mostly irrelevant
- LDAP and `net user` dumps where a description field holds a password
- HTTP response headers and page source: a framework version, a commented-out endpoint, a cookie flag
- `ps aux` / `netstat -tulpn` where a locally-bound service is the pivot target
- Directory listings and file timestamps where one file is out of place
- **No-lead scenarios in every family** (D9), unmarked as such, so the possibility is always live

**Content source and the honesty rule.** Ground truth comes from the 191 PEN-200 writeups at `Cyber Security Study and Reference/OffSec/Pen-200/Boxes`, which record stage by stage which observation actually mattered, and frequently name it outright ("the dropdown's exact engine list is the tell"). The *noise around it* is synthesized (D10). A scenario's provenance field names the writeup so a wrong key can be traced and fixed rather than argued about (D11).

---

## Track: salvage

**The mechanic.** crux stands up an instrumented mock service on loopback and hands you a PoC that does not work. You open it in your own editor, fix it, run it. crux reads the service's hit record and tells you whether it landed. The tier is `verified` throughout: the service knows what a correct request looks like because crux wrote the service (D2, D7).

**The defect classes**, which are the real content spine:

| # | Class | What it teaches |
|---|---|---|
| 1 | Python 2 idioms: `print` statement, `urllib2`, implicit str/bytes | The most common single reason an exploit-db PoC will not start. `python2` is not on this machine, which is the realistic condition |
| 2 | Hardcoded attacker IP and callback port | Read the script for what it assumes about *you*, not just the target |
| 3 | Moved endpoint, renamed parameter, changed method | The PoC was written against a different minor version |
| 4 | Missing `Host` header, cookie, CSRF token, or auth step | The exploit assumes state the script never establishes |
| 5 | Payload needs re-encoding: URL, double-URL, base64, unicode | Encoding is where working exploits go to die |
| 6 | Offset and length arithmetic that is off by a known amount | Offset reasoning outlives the buffer overflow that is no longer on the exam |
| 7 | Assumes `bash`, `python`, or `curl` exists on the target | Portability of the payload, not of the exploit |
| 8 | Imports a package that is not installed and does not need to be | Replacing a dependency with stdlib, under time pressure |
| 9 | **Silent failure**: exits 0, prints `[+] Success!`, does nothing | Never trust a script's own report. Verify the effect, not the message |
| 10 | **Hostile PoC** (D19): exfiltrates or backdoors the payload | Read it before you run it. crux scores this one by watching you fail it |

Classes 1 through 5 are Phase 3. Classes 6 through 10 are Phase 4, with 10 as the track capstone.

**Engineering note.** The mock services follow hone's `netlab` insight exactly: rather than pointing you at someone else's host, **the trainer becomes the host**. It opens listening sockets it owns, records what arrived, and closes them on teardown. `mockhttp.py` and `mocktcp.py` are the two shapes; both expose the same hit-record interface so the scenario schema does not care which it is talking to.

---

## Track: conduit

**The mechanic.** crux builds a real multi-hop topology out of unprivileged network namespaces and drops you into a shell in the attacker namespace. A service exists that is reachable only from a middle host. You build the tunnel. crux then runs a probe from where it must succeed and reports whether bytes actually traversed the path you built.

**This is `verified`, not simulated**, and that is the point of the track. Confirmed working on this machine 2026-08-20 with no root:

```bash
unshare -Urn --map-root-user sh -c 'ip link add v0 type veth peer name v1 && ip addr add 10.9.0.1/24 dev v0 && ...'
nsenter --net=/proc/$SUPERVISOR_PID/ns/net ip -o link      # sibling joins the held namespace
```

**Topologies**, in order:

1. Two hops, one forward. Attacker cannot reach `10.10.2.5:80`; the pivot can. Build `ssh -L`.
2. Reverse the direction. The middle host cannot reach you; build `ssh -R` and understand why the flag flipped.
3. Dynamic. Several targets behind one pivot; build `ssh -D` and drive it with `proxychains4`.
4. No SSH available. Same problem, `socat` relays only.
5. Three hops. Chained forwards, and the moment where people write the second `-L` against the wrong side.
6. Port already bound, or a listener that will not bind on the pivot. Diagnosis rather than construction.
7. `chisel` and `ligolo-ng` variants, declared in `needs` with install routes, skipped cleanly when absent (the hone pattern for texlive and binutils).

**The main engineering risk, and the Phase 5 spike.** The supervisor process must hold several namespaces open for the life of a scenario while the user works in an interactive shell inside one of them, and it must tear all of it down cleanly on exit, crash, or Ctrl-C. Namespaces that leak are namespaces that confuse the next scenario. **Spike this before writing any conduit content**, and if it cannot be made reliable, the track degrades to `graded` topology planning under D14 and says so on every task rather than pretending.

`sshd` at `/usr/bin/sshd` can be run unprivileged on a high port inside a namespace with a generated host key and a scenario-local config, which is what makes topologies 1 through 3 possible without touching the system's real SSH.

---

## Track: lineage ✅ 2026-08-24 (engine and six collections)

**The skill.** Reading an Active Directory collection and choosing a route
through it. Not finding *a* route: finding the one worth taking.

**The mechanic.** You hold one account and you are told which principal you
have to end up holding. `m` opens the collection: every principal, every right
out of it, whether or not you can use it yet (D27). Back on the moves, the list
is the rights you can use **now**, each with what using it costs (D26). Enter
buys one, your holdings grow, and the moves grow with them. Group memberships
are free, transitive and never offered as moves, because a membership is a
state rather than an action; the closed set of what you hold is on screen
instead, which is where the "you already had it" lesson lands.

**The budget is computed, not authored:** twice the cheapest route, floored, so
one real mistake is survivable and two are not. Authoring it per scenario would
drift from the graph the first time an edge moved.

**Scoring.** What you spent against what the cheapest route cost, so the
cheapest route is 100 and double it is 50. **Arriving expensively still
arrives**, which is the point: the trap scenario's wrong answer works, and a
trap that failed outright would teach "do not press that" rather than the thing
that transfers. Not arriving is worth nothing, and how close you got is
reported prominently and kept out of the score, exactly as a `salvage` script
meeting three of four conditions is.

**What the debrief shows.** Your route, priced. Anything you paid for that led
nowhere, which is the graph's version of `sift`'s "what you chased". The
cheapest route with a sentence against each step saying what made it cheap. And
where the graph has the gap, **what a map that counts edges would have drawn
instead**, side by side with what it costs.

**Content, and how it is audited.** Three collections so far. Each authors the
*structure*, because the structure is the exercise; names, ordering and padding
are drawn per seed (D10), and `validate.py` proves the cheapest route is the
same set of rights at all eight probe seeds, the same key-stability check
`sift` gets. Each also declares **what it teaches**, and that claim is proved
against the built graph rather than believed:

| Scenario | Teaches | What `validate.py` proves |
|---|---|---|
| `lineage-reset` | `cost` | the fewest-edges route really does cost more than the cheapest one (reset vs. session) |
| `lineage-culdesac` | `reach` | a branch out of what you hold really does fail to reach the objective, and costs something to enter |
| `lineage-nested` | `nesting` | you really do start holding more principals than you were handed, through nested groups |
| `lineage-delegation` | `reach` | the only arriving route runs through a delegation edge, and the strongest-looking rights are dead ends |
| `lineage-laps` | `quiet` | the cheapest route writes nothing, while an equally affordable route that arrives does write |
| `lineage-dcsync` | `reach` | the objective is the krbtgt hash, and the route that stops at Domain Admins never reaches it |

**A fourth `teaches` value, `quiet`, landed with `lineage-laps`** and is the one worth calling out. Cost and noise are different axes: reading a LAPS password and resetting an administrator's password can cost the same and differ entirely on what they leave behind. `WRITES` in `lineage.py` partitions the rights that change the directory from the ones that only read it, `validate.py` proves a `quiet` scenario's cheapest route writes nothing while an affordable arriving alternative does, and the greedy-cost ceiling is deliberately waived for `quiet` (its two routes cost the same by design, so a cost-only strategy is *meant* to score full marks; the reading it trains is noise, which the cost simulator cannot see).

**And a strategy is measured rather than assumed.** `validate.py --paths`
prints what "always take the cheapest visible move" scores across seeds, the
lineage answer to `--scores`. It earned its keep immediately: the first drafts
of two scenarios scored 85 and 82 against that strategy, meaning a student who
never opened the collection would nearly have won. Both gained cheap branches
that go nowhere, and greedy now scores 38 and 70. **The fix was a better graph,
never a harsher scorer**, which is the same rule `GREEDY_CEILING` follows one
track over.

**Still to do on this track**, and it is content rather than engineering: more
collections. The engine covers the shapes that matter (priced rights, nesting,
cul-de-sacs, sessions, delegation, replication, the read/write noise axis, two
arriving routes at different prices) and nineteen edge kinds are priced, of
which the six scenarios now use sixteen. The three unused kinds
(`AllExtendedRights`, `AllowedToAct`, `ReadGMSAPassword`) are each a real shape
a future collection can turn on.

---

## Track: proctor ✅ 2026-08-24

**The skill.** Allocation and abandonment. The skill tracks each ask
whether you can do a thing; none of them asks what you do when there is more
work in front of you than clock behind you. That decision has two halves and
neither is taught anywhere: how much of the budget a piece of work is entitled
to, and when to walk away from one that is not paying.

**The mechanic.** A **sitting** is several scenarios against one budget that
never stops. Each leg gets a **share** of that budget, weighted by track, and
the share is not a par time: it is what that leg is entitled to if the budget
is spread evenly across the work. Cross it and you are spending the next leg's
clock. One new verb, `X`, walks away from the leg you are on: you take the zero
and you keep the time. The sitting ends when the budget is gone, not when the
work runs out, so legs you never reached score nothing and say so.

**The post-mortem is the point, and the score is the small half of it.** What
the result screen leads on is `sunk` (D25): minutes spent past a leg's own
share on a leg that then scored zero. It also shows where the rest of the clock
went, which legs were walked away from and whether the call came early or late,
and which legs the clock ate before you reached them. `p` on the track list
opens the same analysis over your whole history rather than one sitting.

**Built as a controller on the existing `on_done` seam, not a fourth engine**,
exactly as chain mode was (D24). A leg is an ordinary `MarkScreen`,
`SalvageScreen` or `ConduitScreen`; what a sitting adds is the clock, the
share, the abandon verb and the ending. Two things had to reach every screen a
sitting builds, and both are cross-cutting rather than per-engine, so they live
on one module-level hook beside `OPEN_HELP`: the remaining budget, folded into
whatever header is on screen, and the abandon key, added to whatever footer is
on screen. A timed sitting whose clock is invisible while you work is not a
timed sitting, and a key that works but is never advertised is screen contract
rule 4 broken.

**Composition, and why it is drawn rather than authored.** A sitting names
tracks and optional pools, not scenario ids, and fills each slot with what you
have **not played**, then what you played longest ago, spreading across
families on the tie-break. A fixed playlist would measure less every time it
was replayed, because a student who knows where the lead is does not overrun.

**Three sittings, three different arguments.** A short one where the budget
fits, so the mechanic is learned before it costs anything. A standard one that
fits only if nothing goes wrong. And **one that cannot be finished**: six legs,
a budget sized for about half of them, and a pass mark that clears on the four
short ones. Nothing on screen says so, because being told is worth nothing and
working it out at minute nineteen is worth a great deal.

**What it does not claim.** crux cannot make anyone sit twenty-four hours, and
the intro screen says so in as many words. A compressed sitting trains the
allocation and the walking away. Endurance is not on offer, and calling a
forty-minute run an exam would be the same class of lie as simulating a
verification and reporting it as one (D14).

---

## Chain mode (Phase 7, extended 2026-08-24) ✅

One scenario carried through all three tracks: sift the output to find the lead, salvage the PoC that exploits it, conduit your way from that foothold to the next subnet. This is the reason the three tracks are one program rather than three, and it is the closest thing crux has to a box.

**Built as a controller plus an `on_done` seam, not a fourth engine.** Each play-screen gained one optional callback: when a stage completes, instead of stopping at its own result it calls `on_done(score)`, and the `Chain` controller stores the score and builds the next stage or the final engagement result. That is the whole mechanism, and it means a chain leg is the identical code path to standalone practice, verified the same way, with only the ending changed. A stumble never blocks the engagement: you always reach all three stages and the result reports honestly which fell, which is the difference between "you rooted it" and "you got a foothold and could not move". `chain` is a fourth section in the loader and on the picker, kept out of `TRACKS` so everything meaning "the skills" still means exactly that; `SECTIONS` is what means "all content".

**Extended 2026-08-24 to a four-stage form, and the Aldwych engagement.** A chain was exactly `(sift, salvage, conduit)` until `lineage` existed; now it is any **prefix of the engagement order** `(sift, salvage, conduit, lineage)` of length three or four (`CHAIN_ORDER` in `validate.py`). The prefix rule keeps the fiction a pipeline, a chain that ran salvage before sift would teach the wrong sequence, while letting an Active Directory engagement carry the fourth stage where the domain half of the exam actually ends. The seam did not change: a lineage stage is an ordinary `WalkScreen` with an `on_done` callback, the same as the other three. What had to change was small and is the same generalisation `proctor` needed: `_passed` gained a lineage arm (arriving is the win, as landing is for conduit), `_stage_line` now reads `total` or `total_score` off whatever the stage returns rather than branching per track, and a lineage stage is `graded` like sift. `chain-aldwych` is the engagement: an anonymous LDAP dump with a password in a `description`, a template injection whose PoC was written for the previous version, a forward with a typo'd destination port, and a graph from that same service account to Domain Admins whose shortest path is its loudest. Every leg is run for real by `validate.py`, and the lineage leg is proved solvable by `check_lineage_body` exactly as a standalone collection is.

---

## Content schema

```python
Scenario(
    id="sift-nmap-highport-01",
    track="sift",
    title="Full-port scan on a quiet Linux host",
    tier="graded",                       # D6
    order=10,
    source="Boxes/Linux/HackTheBox/Busqueda/Busqueda - Writeup.md",   # D11
    waypoint="light-scan",                # D11, one of the 174 known node ids
    hone=["nmap", "ffuf"],                # optional, tools this leans on
    needs=[],                             # binaries required, with install routes
    seed=8412,                            # D10
    body=...,                             # per-track payload
)
```

Per-track payload: `sift` carries the fixture spec, the key (line ids that are leads), the decoys worth naming in feedback, and the action choices. `salvage` carries the defect class list, the broken source, the service spec, and the hit condition. `conduit` carries the topology spec and the probe. The two composite sections (D24) carry schedules rather than exercises: `chain` carries its stages, and `proctor` carries a budget, a pass mark and the slots to spend the budget on. Neither carries provenance of its own, because the provenance rides on the scenarios they schedule, where it was already audited.

`validate.py` is authoritative on counts and must be able to prove, at minimum: every scenario id is unique, every `waypoint` value is a plausible node id, every `source` path exists when the vault is reachable, every `sift` key line is actually present in the fixture the seed produces, every `salvage` scenario's reference solution makes the mock service record a hit, and every `conduit` topology tears down without leaking a namespace. **The reference-solution check is the one that matters most**: it is what proves content is solvable rather than merely well-formed, and it is exactly the check that made hone's adapter content trustworthy.

---

## Build phases

### Phase 0: Harness, no content ✅ 2026-08-20
Screens, input layer, state, track select, scoring module, injected clock, `validate.py`, `test.py`, `build.sh`. One throwaway scenario in each track to prove the loop runs.
**Done when:** `crux.pyz` builds and runs, track select works, both suites are green. **All met.** A third suite, `test-tty.py`, was added unplanned; see the session log for why.

### Phase 1: sift engine and first content ✅ built 2026-08-20, gate open
Line-marking widget, the two-beat spot-then-act flow, the seeded fixture builder, precision/recall scoring with decoy cost. First families: `nmap`, web content discovery, `sudo -l`. Includes no-lead scenarios from the start (D9).
**Done when:** the mechanic survives real use by the author. This is a genuine gate; if marking lines is tedious rather than tense, the mechanic changes here and not later. **Everything is built and every suite is green, but the gate is a judgement only the author can make, and it is still open.**

One deviation worth recording: the plan said `ffuf` and the content is authored as `feroxbuster` output. The corpus decided it. Across the 191 writeups the counts are gobuster 27, feroxbuster 19, ffuf 15, and feroxbuster's output carries status, size, lines and words in columns, which is what makes the size-anomaly scenarios readable. The skill transfers; the column layout is what had to be picked.

### Phase 2: sift to breadth ✅ 2026-08-20
Remaining artifact families. Decoy cost tuned against real scores rather than guessed. Provenance populated and audited against the writeups. **All three done.** Four new families (SMB, local enumeration, listening sockets, directory dumps) plus a two-scenario HTTP family, taking sift from eleven scenarios to twenty-six. `DECOY_WEIGHT` profiled across the whole content set and kept at 2.0 on the evidence. Provenance now audited automatically against the vault by `validate.py`.

The one item from the family list deliberately not built: **directory listings and file timestamps** as a family of their own. It folded into the local-enumeration family instead, where a timestamp is one of the tells rather than the whole screen, which is how it reads in real output.

### Phase 3: salvage engine, defect classes 1 to 5 ✅ 2026-08-20
`mockhttp.py`, `mocktcp.py`, the hit-record interface, the edit-and-run loop, reference solutions wired into `validate.py`. **All done.**

Two design points worth keeping. First, **the hit record scores each request against single-purpose requirements and reports the closest attempt's first unmet one**, so a failed exploit produces "the base value arrived but the injection did not survive" rather than "it did not work". That was the difference between a verifier and a teacher, and it is why requirements check one thing each. Second, **the score is binary**: an exploit meeting three of four conditions does not work, and awarding 75 for it would teach something false. The partial progress is shown prominently and does not enter history.

### Phase 4: salvage to breadth, classes 6 to 10 ✅ 2026-08-20
Ending on the hostile-PoC capstone (D19). **Done.** Classes 6 to 10 are length arithmetic over a newly framed TCP target, a payload written for bash against a busybox appliance, a pwntools import with no way to install it, a script that prints success unconditionally, and the hostile mirror build.

Three things this phase added to the harness rather than to the content. `MockTcp` gained **length framing** that records only the framed body, without which a truncated frame would score identically to a whole one. `SalvageBody` gained a **trap sink**, a second loopback service the script must never contact, which is what turns "read it before you run it" from advice into something crux can observe. And the result screens became **scrollable**: the height backstop was silently truncating the debrief, so on a 24-row terminal a student got the score and lost the explanation.

### Phase 5: conduit spike, then engine ✅ 2026-08-20
**The spike came first and it succeeded.** Every question it was set turned out to be answerable, though not by the design that was planned.

**The planned architecture was abandoned, and that is the main result.** A long-lived supervisor holding namespaces open while the student works in an interactive shell inside one is more realistic and a great deal more machinery: a control protocol, hand-off of the real tty to a process inside a user namespace, and a supervisor whose death has to be survivable at every point. The build takes about two seconds, so **each attempt now builds the whole network, runs your tunnel script in the attacker namespace, probes, reports and exits.** Teardown stopped being a problem to solve and became a consequence of the process ending, and the exercise became the same shape as salvage: edit a file, run it, be told exactly what did and did not happen.

**Six things had to be discovered to make `sshd` work unprivileged**, none of them guessable and all recorded in `crux/targets/netns.py`: `--map-auto` rather than `--map-root-user`, because privsep needs to `setuid` to a user that must exist inside the namespace; a bind-mounted privsep directory, because the real one reads as `nobody`; crux supplying its own `passwd`/`group`/`shadow`, because sshd read the host `/etc/shadow` and refused the login on the grounds that root is locked there; a tmpfs home, because `authorized_keys` is read as the logging-in uid which cannot traverse a `0700` directory owned by someone else; `lo` brought up, because a fresh namespace has it down and a forward to `127.0.0.1` fails with "network is unreachable"; and the host key read as root while the public key is read as the user.

### Phase 6: conduit content ✅ 2026-08-20
Topologies 1 to 6, then the optional `chisel` / `ligolo-ng` variants behind `needs`. **Done, seven scenarios.** Reverse forward, dynamic SOCKS, three-hop chain, blocked-forwarding diagnosis, and the chisel agent joined the two from Phase 5.

Three engine additions the content needed, all data rather than new machinery: a **SOCKS5 probe** spoken in stdlib (the only way to verify a `-D` dynamic forward, and done by hand rather than borrowing `proxychains` so the thing under test is the proxy and not the client); **per-scenario `sshd` config**, so the blocked-forwarding scenario can set `AllowTcpForwarding no` without leaking it to the next run; and **`needs`-gating**, so a scenario naming a tool you have not installed greys out with an install pointer and scores nothing, the same courtesy hone extends to a module whose tool is absent.

### Phase 7: chain mode ✅ 2026-08-20
See the Chain mode section above. Done: the Wexler Corp engagement, three stages, each a real run of its track, ending on a recorded engagement scored by how much of the box fell.

### Phase 8: proctor ✅ 2026-08-24
Track four: the pacing track, built on the D12 time data that has been recorded since Phase 0. See the *Track: proctor* section above for what it is. **Done, three sittings.** `pacing.py` holds every number the track reports as a pure function of recorded attempts, `screens/proctor.py` holds the controller and the four screens, and the sittings are authored content like everything else.

**The D12 bet paid.** Nothing needed backfilling: `elapsed` had been on every attempt since the first commit and the whole track is built on it. Two fields were added for what a sitting alone knows, `sitting` and `abandoned`, and they are the same argument one level down: a zero you chose at four minutes and a zero you fought for at twenty are opposite outcomes, and a history storing only the score could never tell them apart afterwards.

**Two harness bugs found, and the second was pre-existing.** Adding an abandon key to a marking screen that was already exactly at the frame width pushed a hint off the edge: the key was advertised, clipped, and therefore not advertised at all. The footer now **wraps** rather than truncating, which fixes the class rather than that one screen, and `test.py` now checks every promised key against the rendered *frame* instead of against the hint list. That check immediately found the same fault sitting there already: **`? help` had been clipped off `MarkScreen` at 80x24 since the pan hint was added**, on the narrowest terminal crux claims to support, with nothing to do with `proctor`. Separately, a long scenario title plus a running clock tore the top border open, because `box_top` clipped the whole line and took the corner with it. The header now gives the *title* away first, since the title is the half that is already on screen elsewhere, and `test.py` asserts every frame still closes on its own corner at every width.

**One arithmetic bug the screens found that the tests had not.** The sunk-time note counted the wrong population: it reported the minutes correctly and then attributed them to `dry` legs (ridden to the end), so a sitting where both overruns ended in a late walk-away printed *"14m 40s went past your own allocation on 0 legs"*. `sank` and `dry` are genuinely different sets and now both exist. It was found by rendering the screens and reading them, which is worth remembering: 39,000 green checks did not catch a sentence that contradicted itself in the middle.

**`TRACK_WEIGHT` is a labelled estimate, and that is a deliberate difference from `DECOY_WEIGHT`.** The decoy weight could be settled from the content alone, because what a greedy answer scores is a property of the authored screens. How long a leg takes is a property of a person, so only recorded play can settle it, and there are two attempts in this history. `validate.py --pacing` prints the weights beside whatever the real medians say and **declines to draw a conclusion under eight completed attempts per track**. The estimate being provisional is fine; a guess presented as a measurement would not be.

### Phase 9: lineage ✅ 2026-08-24 (engine and six collections)
Track five, and the last of the two that were sketched alongside crux and are the reason D5 exists. See the *Track: lineage* section above. **Engine done, three collections authored.** `crux/lineage.py` is the prices, the closure and the two searches; `crux/targets/_graph.py` is the seeded collection builder; `crux/screens/lineage.py` is the walk, the collection and the debrief. `lineage` joins `TRACKS` rather than `COMPOSITE` (D24), because unlike `chain` and `proctor` it is a fifth thing a person can be good at.

**One search function, not two.** The cheapest route and the fewest-edges route differ only in what an edge is worth, so `_search` takes the weighting and both callers pass a lambda. The first version was two functions and they had already drifted on how they treated free edges before either was called.

**Two bugs, and the second is the more interesting one.** A hand-written probe graph caught `dead_ends` calling the **winning move** a dead end: the last step of a clean walk buys an account with no priced rights out of it, because it is the end of the road on purpose, and "nothing leads out of here" was true of it in the same way it is true of a cul-de-sac. A student who played perfectly was being told they had wasted their winning move. And a test that asserted against `render()` rather than `content()` was really asserting about the scroll position, since the debrief is longer than a terminal; that one was a bad test rather than a bad screen, but it is the same confusion that let the height backstop eat a debrief back in Phase 4.

**The `teaches` field is the idea worth reusing.** Content declares the property it exists to demonstrate and `validate.py` proves that property against the built graph. A claim in a docstring is a claim nobody rechecks; a claim in a field that a checker recomputes cannot rot when an edge moves.

### Phase 10: the four-stage engagement ✅ 2026-08-24
The last unbuilt composition. A `lineage` leg already ran inside a sitting; a chain did not, and that one was a real decision rather than a line of content because the chain contract was deliberately the three-track "find, land, reach" engagement. **Done: the contract is now a prefix of `CHAIN_ORDER = (sift, salvage, conduit, lineage)` of length three or four, and `chain-aldwych` is the four-stage engagement.** See the *Chain mode* section above. The stage-order check that has caught real bugs is preserved as the prefix rule, `validate.py` runs the new engagement's salvage and conduit legs for real and proves its lineage leg solvable, and `test.py` drives it stage to stage through the capstone.

### Later, not scheduled
More `lineage` collections and more `chain` engagements, both purely content now. **Every composition the design allows exists at least once**: a lineage leg in a sitting and a lineage stage in a chain both work, so nothing further is a new capability. The three unused edge kinds (`AllExtendedRights`, `AllowedToAct`, `ReadGMSAPassword`) and a second four-stage engagement are the obvious next instances if the track ever wants them.

---

## Environment findings (2026-08-20)

Recorded so they are not re-derived. All checked on this machine.

| Check | Result |
|---|---|
| Python | 3.14.7 |
| Unprivileged user namespaces | Enabled (`unprivileged_userns_clone=1`, `user.max_user_namespaces=254950`) |
| `unshare -Urn --map-root-user` + veth pair | **Works, no sudo** |
| Sibling joins held netns via `nsenter --net=/proc/PID/ns/net` | **Works** |
| `sshd` | Present, `/usr/bin/sshd` |
| `socat`, `proxychains4`, `ncat`, `nc`, `gcc`, `ip`, `unshare` | Present |
| `chisel`, `ligolo-ng` | **Absent**, so `needs`-gated (D14) |
| `python2` | **Absent**, which is the realistic condition for defect class 1 |
| PEN-200 writeups | 385 files under `OffSec/Pen-200/Boxes`, stage-structured, **174 distinct Waypoint node ids referenced** |

---

## Open questions

1. **Does line-marking survive contact?** The whole `sift` track rests on it. Phase 1 is the gate and the mechanic is allowed to change there.
2. **How much noise is realistic without being tedious?** A real `linpeas` run is thousands of lines. Some compression is necessary; too much deletes the skill. Needs calibration against real scores, not a guess.
3. **Can the namespace supervisor be made reliable?** Phase 5 spike. D14 is the answer if not.
4. **Waypoint node titles: read Waypoint's data files at runtime, or vendor a node list?** Vendoring drifts; reading needs to locate Waypoint the way hone locates the vault via `WAYPOINT_VAULT`. Decide in Phase 1 when the first link is actually needed.
5. **What are the track weights really?** `pacing.TRACK_WEIGHT` is an estimate (sift 1, lineage 2, salvage 3, conduit 3) and is labelled as one everywhere it appears. It cannot be settled without eight or so completed attempts per track from a real person; `validate.py --pacing` is the instrument and it currently declines to answer. Revisit once the history is deep enough, not before.
6. **Are the `lineage` edge prices right?** They are a defensible ordering rather than a measurement, and unlike `TRACK_WEIGHT` no amount of play will settle them: they encode a judgement about noise and reversibility that a trainer has to make on somebody's behalf. The ordering is what carries the lesson; if an individual number is ever argued with, argue about the ordering it implies rather than the number.
7. **Does a sitting stay honest on replay?** Slots draw unseen content first, which holds for as long as there is unseen content. After that a sitting is being played by someone who knows the answers, and it measures less. The authored fallback if it turns out to matter is a pool per slot rather than a whole track, which is already supported and unused.
8. **Should `sift` fixtures ever be *this machine's* real output** (a scan of crux's own loopback sockets, the hone `netlab` trick)? It would raise realism at some cost in determinism. Not needed before Phase 2.

---

## Session log

| Date | What happened |
|---|---|
| 2026-08-24 (d) | **Phase 10: the four-stage engagement, and crux's compositions are complete (still v1.7.0).** The last unbuilt composition was a `lineage` stage inside a `chain`, held back because the chain contract was deliberately the three-track engagement. Widened it the minimal way: a chain is now a **prefix** of `CHAIN_ORDER = (sift, salvage, conduit, lineage)` of length three or four, which preserves the stage-order check (a chain still cannot run salvage before sift) while allowing the AD fourth stage. The seam was unchanged, a lineage stage is a `WalkScreen` with an `on_done` like the other three; the only edits were the same generalisation `proctor` already needed (`_passed` gained a lineage arm, `_stage_line` reads `total` or `total_score` off whatever the stage returns) plus a `graded` tier for the lineage stage and a `check_lineage_body` dispatch in the chain validator. **`chain-aldwych`** is the engagement: a password in an LDAP `description`, a template injection whose PoC targets the previous minor version (endpoint moved v1->v2, field renamed), a forward with a typo'd destination port, and a graph from that same `svc_deploy` account to Domain Admins whose three-edge reset route is louder and dearer than the four-edge session route. Every leg runs for real in `validate.py`; the lineage leg is proved solvable exactly as a standalone collection. `test.py` drives all four stages through the capstone and asserts a clean run passes four of four. One existing test that asserted "every engagement is three stages" was updated to the prefix rule. `validate.py` clean at zero warnings, `test.py` 59,660, `test-tty.py` 65, `dist/crux.pyz` builds and runs. **Every engine is built and every composition exists at least once; what remains is content.** |
| 2026-08-24 (c) | **lineage to six collections, a fourth `teaches` value, and a lineage leg inside a sitting (still v1.7.0).** Three new domains: `delegation` (the only arriving route runs through a `AllowedToDelegate` edge that does not read as a path, while the strongest-looking rights are dead ends), `laps` (reading a LAPS password and resetting an admin cost the same and differ entirely on what they leave behind), and `dcsync` (the objective is the krbtgt hash, and the route that stops at Domain Admins never reaches it). **A new `teaches="quiet"`** splits cost from noise: `WRITES` in `lineage.py` partitions directory-writing rights from read-only ones, `validate.py` proves a quiet scenario's cheapest route writes nothing while an affordable arriving alternative does, and the greedy-cost ceiling is waived for it because its routes cost the same by design. **A content bug the solver caught:** `delegation` was authored as `teaches="cost"` claiming delegation was the cheap route, but controlling a service account and then using its delegation is a write plus the delegation, so a backup-operators route was genuinely cheaper; it is `reach` now and the debrief says why delegation can never be the single cheapest edge. **A checker bug the LAPS graph caught:** the quiet check deleted the cheapest route's edges and re-solved, which took a shared tail with it and reported no loud alternative; replaced with `cheapest_through`, which forces a route through one edge without deleting anything. **D24's promise cashed:** the standard sitting now runs a lineage leg, which needed `proctor`'s score reader generalised from `total if sift else total_score` to reading whichever attribute the leg's engine actually exposes (a lineage `WalkScore` has `total`, no `total_score`, and would have crashed the sitting the first time one was drawn). Sixteen of nineteen edge kinds now used. `validate.py` clean at zero warnings, `test.py` 59,622, `test-tty.py` 62, `dist/crux.pyz` builds and runs. |
| 2026-08-24 (b) | **Phase 9: `lineage`, the fourth skill track (v1.7.0).** Track five of the D5 sketch, and the last engine crux was missing. You hold one account in a synthetic Active Directory collection and have to end up holding another; `m` opens the whole collection unfiltered (D27) and the moves list shows only the rights you can use, each priced. **The prices are the track** (D26): a collection tool ranks routes by edge count, and an edge is not a unit of anything, so the cheapest route is routinely not the shortest and the grade is what you spent against what the cheapest cost. Arriving expensively still arrives and scores less, which is deliberate: a trap that failed outright would teach "do not press that". `MemberOf` is free, transitive and applied by closure rather than offered as a move. **Three collections, each proving a different claim, and the claim is checked rather than believed:** the `teaches` field names the property and `validate.py` recomputes it against the built graph, so `teaches="cost"` fails unless the fewest-edges route really does cost more. Same key-stability contract as `sift`: the cheapest route must be the same set of rights at all eight probe seeds. **`--paths` earned its keep on its first run**, the lineage answer to `--scores`: it measures what "always take the cheapest visible move" scores, the first drafts of two collections scored 85 and 82 against it, meaning a student who never opened the map would nearly have won, and both gained cheap branches that go nowhere until greedy fell to 38 and 70. The fix was a better graph, never a harsher scorer. **Two bugs.** `dead_ends` called the *winning* move a dead end, because the last account on a clean route has no priced rights out of it in exactly the way a cul-de-sac does not, so a perfect walk was told it had wasted its final move; caught by a hand-built probe graph. And one new test asserted against `render()` where it meant `content()`, so it was really asserting about a scroll position. `validate.py` clean at zero warnings, `test.py` 59,287, `test-tty.py` 62, `dist/crux.pyz` builds and runs. |
| 2026-08-24 | **Phase 8: `proctor`, the pacing track (v1.6.0).** Track four, and the first thing built on the D12 bet: `elapsed` has been on every attempt since the first commit, nothing needed backfilling, and the whole track stands on it. A **sitting** is several scenarios against one budget that never stops; each leg gets a **share** of that budget weighted by track; `X` walks away from a leg and keeps the clock; the sitting ends when the budget does, so legs you never reached score nothing. Three sittings, and the third **cannot be finished on purpose**: six legs, a budget for about half, and a pass mark that clears on the four short ones. `pacing.py` holds every reported number as a pure function of recorded attempts (D17 holds: nothing there reads a clock), and `sunk` is the headline (D25): time past a leg's own share on a leg that scored zero. Slots draw **unseen content first**, then least-recently-played, spreading across families on the tie-break, because a fixed playlist measures less on every replay. `chain` and `proctor` were pulled out of `TRACKS` into a new `COMPOSITE` (D24): neither authors an exercise, both schedule the three that do. **Two harness bugs, and the second was already shipping.** The abandon key pushed `MarkScreen`'s footer past the frame and was clipped, so a key the footer promised did not exist; footers now wrap, and `test.py` checks every promised key against the rendered *frame* rather than the hint list. That new check immediately found **`? help` had been clipped off `MarkScreen` at 80x24 since the pan hint landed**, nothing to do with proctor, on the narrowest terminal crux supports. Separately a long title plus a running clock tore the top border open; `box_top` now gives the title away rather than the corner, and every frame is asserted to close at every width. **One bug the tests could not have caught:** the sunk note counted `dry` legs (ridden to the end) while summing `sunk` minutes (which include late walk-aways), printing *"14m 40s went past your own allocation on 0 legs"*. Found by rendering the screens and reading them, at 39,000 green checks. **`TRACK_WEIGHT` is a labelled estimate and stays one:** unlike `DECOY_WEIGHT` it cannot be settled from content, only from play, and `--pacing` declines to read a median under eight completed attempts per track. `validate.py` clean at zero warnings, `test.py` 39,794, `test-tty.py` 54, `dist/crux.pyz` builds and runs. |
| 2026-08-20 (u) | **Reset progress, and a work-file bug it uncovered (v1.5.0).** Asked for a way to reset progress; building it found two bugs in the same code that had to go first, because a reset means nothing if the app resets your files behind your back. **`salvage` rewrote your script from the original on every open**, silently destroying repairs between visits, while **`conduit` never rewrote it**, so a mangled script could not be recovered: one threw work away, the other trapped you in it. Both keep the file now and both restore on request. Keeping it needed `crux/progress.py` rather than a one-line `if not exists`, because the mock target takes an **ephemeral port**, so the address crux injected last time is dead on return: rewriting the file would destroy edits, leaving it would point at nothing. crux records exactly which strings it injected in `.crux-meta.json` and swaps **only those**. That precision is load-bearing, since `salvage-address` is *about* a hardcoded `127.0.0.1:4444` callback the student must keep, and a blunt "rewrite anything local" would break the exercise it was meant to help; both directions are tested. Three reset surfaces, because reset means different things: `--reset [history|work|all]` (states the damage, asks, points at `--export`, `--yes` skips), `R` on the home screen (a screen listing what is on disk, every option needing a second keypress), and `R` twice inside a salvage or conduit scenario to restore just that script. |
| 2026-08-20 (t) | **Result screens redesigned to teach (v1.4.0).** Reported from real use: at the end of a sift scenario it was not clear what you got right or wrong, and the last screen missed the chance to explain. It did. The old screen printed a score and bare `missed`/`chased` labels, leaving the student to work out why the line they skipped was the lead and why the one they chased was a trap, **which is the entire lesson of the track**. `Line` gained a `why`, and all **87 leads and decoys** across every sift scenario and both chain sift stages now carry one. The result is a marked-up copy of the key under headings that name the verdict: *What mattered* (every lead, found or missed), *What you chased* (decoys and noise told apart), *What you left alone, correctly* (decoys refused, which was never acknowledged), *What you decided to do*, and *The habit*. The headline became a sentence rather than a band name: "You missed the way in, and went after 2 that was not it." Also fixed: the salvage result appended its requirement hint to the same line, where the frame clipped it and threw away the only sentence saying what was still wrong; it wraps underneath now. Guarded both ways, `validate.py` warns on any key line that explains nothing and `test.py` asserts every explanation reaches the screen, playing each scenario badly on purpose because that is the attempt that most needs explaining. |
| 2026-08-20 (s) | **Status sweep before pausing.** Checked the three sources of truth against `validate.py` rather than against each other, which is what found the drift. The plan's START HERE still claimed one chain engagement (there are two), a signal-scope splash (replaced by the scan-lock), seven sift families (ten) and stale suite counts; the README's status block was still describing v1.0.0 at twenty-six scenarios; and the `MEMORY.md` index line still read v1.0.0. All three corrected and now agree. The START HERE also gained an explicit **Where to pick up** with the three candidates ranked (`lineage`, then `proctor`, then more engagements) and the one open question recorded: the `source` field still points at the local corpus, is never displayed (D23), and is what `validate.py` audits, so removing it would cost the check that has caught four real content errors. The project memory was rewritten from a single wall of text into state, the three rules that are expensive to rediscover, and the verification contract. |
| 2026-08-20 (r) | **No third-party attribution anywhere the program shows (v1.3.0, D23).** On instruction: crux names the technique and the CVE, and never a platform, course, vendor or individual machine. `provenance.py` was rewritten to return `a real attack chain` or `real-world tradecraft` in place of `Busqueda (HackTheBox)` and `PEN-200 methodology`. The help screen answer to "are these real?" was rewritten the same way, and it still names the CVEs because those are the grounding worth having. Fixture identifiers that echoed machine names were renamed to neutral fictional ones (`cicada.htb` -> `harbord.local`, `hollow.vl` -> `sentinel.local`, `app.mirage.vl` -> `app.mirage.internal`, hosts `lavita`/`sau`/`monitored` -> `app02`/`trailsrv`/`monsrv`, `iis apppool\craft` -> `iis apppool\vantage`, `MARKUP\daniel` -> `HARBORD\daniel`, and a `/var/www/html/lavita` path). **The `source` field is deliberately kept**: it is what `validate.py` audits against the local corpus, that audit has caught real content errors, and it is never rendered. `test.py` now walks every displayable string on every scenario plus every help topic against a banned-name pattern, so this cannot regress as content grows; verified by planting a name and watching it fail. |
| 2026-08-20 (q) | **The Northwind engagement: an Active Directory chain (v1.2.0).** The capstone had one engagement and it was a single Linux web host; half the exam is the domain and that shape had no chain. Northwind is the AD shape: something you can reach, something you cannot, and a foothold in between. `sift` on anonymous share enumeration finds `deploy$`, hidden but not protected; `salvage` fixes a Log4Shell proof-of-concept that sprays its payload at `User-Agent`, a header the target never logs (CVE-2021-44228); `conduit` forwards the DC's LDAP, where the starter writes the destination as `127.0.0.1` and so points the far end at itself. Every defect differs from Wexler, and the last one never reports an error because from SSH's point of view everything succeeded. The Wexler salvage leg also gained CVE grounding (Drupalgeddon2). **A real gap in the checks was closed at the same time:** `check_chain_runs` ran each leg's solution but never its starter, holding chain legs to a weaker standard than the standalone tracks, so a chain stage that already worked would have shipped silently. That is precisely the defect that bit the relay scenario in Phase 6. It now runs both and requires the starter to fail, verified by sabotaging a leg and watching the check catch it. |
| 2026-08-20 (p) | **Content accuracy audit and two new sift families (v1.1.0).** The audit found one real inaccuracy: the salvage dependency scenario claimed Baron Samedit "ships as pwntools scripts", which is false (its public exploits are mostly C). Reworded to state what is actually transferable without asserting something untrue about that CVE; the other nine CVE mappings check out. **The gap the audit exposed was structural: all 26 sift scenarios read Linux and network output, while roughly forty of the seventy exam points are Windows and Active Directory.** Two families close it. **Windows privilege escalation** (4): `SeImpersonatePrivilege` on a service account (Craft), a token with nothing on it that closes the whole potato family (Markup), a SYSTEM scheduled task whose script is `BUILTIN\Users:(F)` (Markup), and an unquoted service path crossing a writable directory. **Credential classification** (3): a SAM dump where the empty-LM and empty-NT constants are furniture and the real NT hash needs no cracking at all, four hash formats of which only the Kerberos ticket is worth the GPU, and a no-lead screen of material that is already a credential. `crack-classify` is one of the most-referenced Waypoint nodes in the corpus and nothing drilled it. New fixtures `WhoamiPriv` and `TextBlock`. **A D10 lesson worth keeping:** the first version of both fixtures produced identical screens for seeds 1 and 2, because shuffling a five-row list has few enough orderings to collide. The fix was also the more realistic rendering: a real token lists eight to a dozen privileges and which ones depends on the account, so a seeded subset is drawn from a larger pool, and `icacls`/`sc qc` gained the extra rows those commands really print. Twelve distinct screens over twelve seeds now. sift is 33 scenarios; validate clean, `test.py` 31,730, `test-tty.py` 44. |
| 2026-08-20 (o) | **The rendering bug behind "blue bars", and it was worse than bars (v1.0.5).** Reported as coloured bars left over after the opening. Emulating the terminal (an ANSI screen model tracking per-cell background, fed the real pty output) found the fault: **the main loop wrote bare LF while the terminal is in raw mode**, where OPOST is off and LF moves down without returning the carriage. Every rendered line is exactly terminal-width, so after each line the cursor sat at the right edge, the LF dropped a row, and the next character wrapped to the row after: **every line consumed two physical rows**, the app drew on every other row, and the previous screen (the splash, whose CRUX blocks are cyan and dark blue) showed through the gaps. The splash always converted to CRLF and the main loop never did, which is why the splash looked right and everything after it did not. This also explains the earlier "options are off the screen" report: at half vertical density only half the content ever fitted, and a sift scenario now fills all 24 rows instead of 12. Latent since Phase 0. `test-tty.py` gains a regression check that not one bare LF is written in raw mode, across a first paint and a repaint. A caution recorded for next time: the first background map read as leftover colour was **my emulator** misparsing `38;2;r;g;b` foreground as a background code; the instrument was fixed before its verdict was trusted. |
| 2026-08-20 (n) | **Flicker fix and salvage CVE grounding (v1.0.4).** (1) A reported menu flicker (worst in sift) was the loop erasing the whole screen with `\x1b[2J` and redrawing on every pass, including the twice-a-second idle pass on the read timeout. The loop now repaints in place (home, erase each line to its end, erase below) and only when the frame changed: an idle screen writes nothing at all (measured zero bytes over a 2s idle window), and a changed one draws over the last without a blanking flash. (2) Every salvage scenario is now grounded in a real CVE, shown as "modelled on CVE-XXXX (product), safe local stand-in" and closed with an "In the wild" note on how that defect broke the real public PoC: Drupalgeddon2 (py2), Webmin (hardcoded callback), Apache 2.4.49/2.4.50 (moved payload), ProFTPD mod_copy (command order), Shellshock (encoding), EternalBlue (length arithmetic), Huawei HG532 (busybox), Baron Samedit (pwntools/no-pip), WebLogic (false success), and the real trojaned-PoC incident (the D19 capstone). Targets stay synthetic loopback stand-ins (D7). `SalvageBody` gained `cve`, `models`, `real_note`; `test.py` asserts all three per scenario. `test.py` 30,523, `test-tty.py` 42, validate clean. |
| 2026-08-20 (m) | **Polish from real-use feedback (v1.0.3): splash, guidance, realism.** (1) The splash was rebuilt again into a bold **CRUX scan-lock reveal** that actually spells the name: a bright column sweeps left to right, letters snap in behind it, the word locks (`scanning`->`locked`). (2) Guidance: it was unclear what to do, especially in sift. Each track list now opens with a one-line goal; the sift screen states the mechanic every time (space marks, enter submits, nothing-marked is valid); the `?` help is now **track-aware** (what you are doing / how to play / the catch / scoring, with the right keys). (3) Realism: `crux/provenance.py` surfaces each scenario's real source in-app (`based on Busqueda (HackTheBox)`), which the sources always recorded but nothing showed. A verification pass against the actual writeups corrected two things: the PC loopback scenario now matches the real box (root-owned `rpc.py` on `127.0.0.1:65432`, external 22 + 8000 ttyd, not 22/80 + 50051), and two scenarios wrongly attributed to Busqueda were re-sourced to the methodology. Help now states plainly that sift is modelled on real boxes while salvage/conduit run against synthetic loopback targets on purpose (safety), with real defect classes and techniques. `test.py` 30,473, `test-tty.py` 42, validate clean. |
| 2026-08-20 (k) | **Splash redesigned to be distinct from hone, and a real menu bug fixed (v1.0.2).** The first splash (row j) was too close to hone: same ANSI Shadow block font, same grit dissolve. It is now a **signal scope** entirely of crux's own: a spectrum where a sharp peak climbs out of a noise floor and locks (`scanning` -> `locked`), with the wordmark a compact letter-spaced label beneath, because a peak emerging from noise is the app's own thesis rather than a borrowed silhouette. Same guarded, fully-degrading mechanics. Separately, and reported from real use: the menu let the selection scroll off-screen (`ListScreen` windowed in render rows while the cursor counted items, and the home and track screens draw two rows per item, so the selection descended twice as fast as the window). Windowing is now measured in **item blocks**, keeping the cursor's whole block on screen; a regression test walks every item at cramped heights. The track list was also tightened to one row per scenario with the tier badge folded in on the right, roughly doubling how many are visible. `test.py` 29,372 checks, `test-tty.py` 42, validate clean. |
| 2026-08-20 (j) | **Splash sequences added (v1.0.1).** `crux/splash.py`, forked from hone's proven mechanics (D4): fully guarded so an entrance can never fail a launch, degrading on every rung (no TTY, small window, `--no-splash`, or the ASCII rung all fall back rather than print tofu), skippable with any key. The metaphor is crux's own thesis: the `CRUX` block wordmark **resolves out of grit** on the way in and **dissolves back into noise** on the way out, because finding the signal in the noise is what the whole app trains. The held entrance shows the scope (`26 sift  10 salvage  7 conduit  1 chain`) and names its own exit; the farewell carries the tagline. Wired into `app.run` behind `--no-splash`, and the functional pty suite passes `--no-splash` so its screen assertions are unaffected while a dedicated pty check drives the real animation. `test.py` gained a splash suite across every rung (check count 19,754 -> 24,747); `test-tty.py` 37 -> 42. |
| 2026-08-20 (i) | **Phase 7 complete: chain mode, and crux is v1.0.0.** The Wexler Corp engagement threads all three tracks into one flow: an nmap scan whose lead is a pinned CMS on 8080, that CMS's Python-2 exploit to repair and land, and a pivot from the foothold to an internal PostgreSQL server on a second subnet. **The mechanism is one `on_done` callback added to each of the three play-screens**, so a chain stage is the identical engine to standalone practice and only the ending changes: a finished stage bridges to the next instead of stopping at its own result. `chain` became a fourth loader/picker section (`SECTIONS = TRACKS + (CHAIN,)`), deliberately outside `TRACKS` so the "three skills" semantics `proctor` and `lineage` will extend stay intact. A stumble does not end the engagement: every stage is always reached and the result is honest about which fell, and an unverifiable conduit leg is skippable rather than a dead end. `validate.py` runs the salvage and conduit legs of every chain for real, the same standard as the standalone tracks. All three suites green; the full engagement is driven stage to stage in `test.py` and confirmed reaching "rooted", and walked from the picker into its first stage over a real pty. Stamped **v1.0.0**. |
| 2026-08-20 (h) | **Phase 6 complete: conduit is seven topologies.** Reverse (`-R`), dynamic (`-D` verified through a real SOCKS5 handshake crux speaks itself), a three-hop chain where the second `-L` classically points home, a blocked-forwarding diagnosis that turns on reading "administratively prohibited" as the server refusing rather than the command being wrong, and a `chisel` reverse-SOCKS agent gated on the binary. **`needs`-gating landed as a general feature**: a scenario naming a missing tool greys out with an install pointer and records nothing, and both suites skip it rather than failing. Two bugs found by running the content. The SOCKS probe carried literal `\\x05` bytes that the heredoc turned into real NULs in the source, so it would not compile; rebuilt from `bytes([...])` so the probe body stays pure ASCII and the NULs are made at runtime. And passing that probe to `python3 -c` failed on the embedded NUL a SOCKS request contains, so probes are written to a temp file instead. The blocked and three-hop scenarios also confirmed the value of the starter-must-fail check twice more: both starters are plausible and both genuinely leave the path closed. |
| 2026-08-20 (g) | **Phase 5 complete: the conduit spike succeeded and the engine is built.** Confirmed by building it: a three-host topology unprivileged, `attacker -> target` unreachable while `pivot -> target` works, teardown verified clean after both a normal exit and a `SIGKILL` (namespace count returns to baseline in both), and a real `ssh -L` through a real `sshd` returning the flag. **The planned long-lived supervisor was dropped for a one-shot builder**, which removed the control protocol, the tty hand-off into a user namespace, and the whole class of teardown problems in one decision. Six separate obstacles had to be cleared to run `sshd` unprivileged; all are written up in the module docstring so nobody re-derives them. **Two real bugs found by running content rather than reading it.** A backgrounded process in a tunnel script inherits the output pipe and holds it open, so `subprocess.run(capture_output=True)` waited for an EOF that never came and every failed attempt cost a 45-second timeout instead of a two-second answer; output goes to a file now. And the first relay scenario shipped a starter that **already worked**, because the defect it was built around (backgrounding the local ssh kills the remote command) turned out not to be a defect at all; the new `check_conduit_runs` caught it immediately, and the scenario now turns on a `bind=127.0.0.1` that puts the relay on the pivot own loopback. |
| 2026-08-20 (f) | **Phase 4 complete: all ten salvage defect classes, ending on the capstone.** Classes 6 to 10 authored; `MockTcp` gained length framing (recording only the framed body, so a miscounted header truncates for real); `SalvageBody` gained a trap sink for D19. **The capstone is the only scenario in crux you can fail by pressing a key**, and its broken script deliberately *works*: anything that made it fail at the exploit too would let a student conclude the lesson is "broken scripts are broken". `validate.py` grades trap scenarios on the trap rather than on the exploit, and asserts that modules a scenario needs absent really are, because `requests` turned out to be installed here and a scenario premised on its absence would have passed silently and behaved differently on a Kali box; `pwntools` is used instead, with the guard. **Two defects found and fixed in the harness, both of which had been shipping since earlier phases.** The result screens were silently truncating the debrief on a 24-row terminal, which is the height backstop working as designed and the worst possible thing for it to eat, so there is now a `ScrollScreen` base and the two result screens, the stub and help all use it. And a structural check written for the capstone failed the reference solution for still *defining* the beacon function it never calls; whether the beacon fires is decided by running it, not by searching the text. |
| 2026-08-20 (e) | **Phase 3 complete: the salvage engine runs, five defect classes authored.** `_hits.py` carries the shared `Request`, `Requirement` and `HitRecord`; `mockhttp.py` and `mocktcp.py` are the two targets and expose the same interface. The screen hands the terminal to `$EDITOR` and to `python3` and takes it back, which is the existing suspend/resume path put to its real use. Content is one scenario per class: Python 2 idioms, a hardcoded callback from the author lab, an endpoint moved between minor versions, a skipped protocol handshake, and a payload encoded twice. **`validate.py` now executes every reference solution and every broken script against a live target** and requires the first to land and the second to fail; the whole suite runs in about 1.5s. **Three bugs, each found by a different suite, and each a real defect rather than a bad assertion.** The TCP target stopped reading at the first newline, so the two-line handshake scenario scored its reference solution *lower* than the broken script it was meant to fix, which the new validate check caught immediately. The handover called `input()` unconditionally, so `test.py` hung for two minutes on a stdin nobody was typing into: the pause only makes sense when there was a terminal to give back. And the TCP target recorded on connection close rather than before replying, so a client could read `OK` and ask for the verdict before the record existed, which is exactly what the screen does the moment the subprocess exits. Recording before replying removes the race entirely. |
| 2026-08-20 (d) | **Phase 2 complete; the sift track is done at 26 scenarios across seven families.** New builders: `SmbShares` (in two real output shapes), `PeasChunk`, `NetstatDump`, `LdapUsers`, `HttpResponse`. New families: SMB share enumeration, local enumeration output, listening sockets, directory dumps, and a short HTTP family. Six scenarios now have no lead at all (D9), and `test.py` asserts they stay under half the content so the app does not train the opposite reflex. **Three checks paid for themselves on their first run.** The provenance audit (new, and the plan asked for it) found that three of the first eleven scenarios cited writeups that do not exist, and one was wrong in a way that mattered: the box it should have cited records `/dev` returning **403**, not the 200 the scenario had been authored around, so the content was corrected as well as the citation. The score profile (`validate.py --scores`) found that the `netstat` fixtures were nine lines long, so marking every line scored 31 against the 5 it scores on a realistic screen; the fix was more realistic output, not a harsher scorer. And it found `sift-peas-suid` had no authored decoys at all, so its wrong answers named lines the scorer never charged for. **`DECOY_WEIGHT` is now measured rather than guessed:** at 2.0 greedy marking averages 11 and never exceeds 20; at 3.0 the greedy average only moves to 10 while chasing one decoy on a two-lead screen drops to 57 against 67 for missing a lead, inverting the relationship the scorer exists to express. 2.0 stays. Also closed a real test gap: `test.py` was render-testing two scenarios out of twenty-six, and content is exactly where non-ASCII and overlong lines get introduced. |
| 2026-08-20 (c) | **Phase 1 built.** `crux/targets/_fixture.py` is the seeded builder of D10, with three families: `NmapScan` (with and without `-sV`, and NSE script blocks as the real source of bulk), `FeroxRun`, and `SudoL`. `MarkBody` now holds a fixture rather than literal lines and materialises a fresh screen per attempt; the seed rides on the recorded attempt so a run can be reproduced, and `--seed` pins it. Eleven scenarios authored across the three families, all with real provenance into the PEN-200 writeups and real Waypoint node ids, two of them no-lead (D9). The Phase 0 smoke scenario is deleted. **Three things were discovered by doing rather than planning.** Authoring the domain-controller scan showed that real output is wider than a terminal and the tell is often at the end of the line, which produced D21 and horizontal panning; shortening the line to fit was rejected because a fixture that prints what nmap does not is worthless. The new "key is stable across seeds" check in `validate.py`, written for the defect class the seeded builder introduces, instead caught a different real bug on its first run: three nagiosxi sudo grants shared their first forty characters, so they shared an id, so marking one would have marked all three. That produced D22. And the first size-anomaly scenario contained no anomaly, because noise 200s were drawn from a wide random range and nothing clustered; page sizes now cluster the way pages cut from one template do. `validate.py` clean with **zero warnings**, `test.py` green, `test-tty.py` green. |
| 2026-08-20 (b) | **Phase 0 landed.** `keys.py`, `term.py`, `render.py`, `theme.py` and the screen contract were forked from hone per D4; `config`, `clock`, `model`, `scoring`, `state`, `loader`, `session`, `app` and six screens are new. The scoring arithmetic of D8 and D9 was checked against real numbers before anything was built on it: marking everything on a forty-line screen scores 9, and missing a lead costs exactly what chasing a decoy costs. One smoke scenario per track, with `salvage` and `conduit` carrying honest `self`-tier stubs that record nothing rather than pretending. **Two bugs, both found by tests that did not exist an hour earlier.** The stopwatch was being paused when the marking screen handed it to the act beat, so beat two's time silently vanished from history, which D12 cannot tolerate; the walkthrough test caught it. Then the space bar turned out to have never worked at all, which no unit test could see: `test-tty.py` was written to drive the real app through a pty and found it on the first run, and it is kept as a permanent third suite. The decoder now agrees with the notation for every special key and `test.py` asserts it. `validate.py` clean with one true warning (the smoke fixture has no provenance, which it does not), `test.py` green, `test-tty.py` green, `dist/crux.pyz` builds and finds its content inside the archive. |
| 2026-08-20 | **Project scoped and named.** Came out of a conversation about what to build for OSCP prep beyond Waypoint, hone, and the writeups. Six candidates were sketched; three were selected and bundled into one program on the argument that they are consecutive stages of the same engagement rather than three unrelated drills. Name settled as `crux` after `range`, `SSC`, `quarry` and `assay` were considered and rejected for the reasons in the START HERE block. Feasibility probes run before writing anything: unprivileged namespaces, `nsenter` join, `sshd`, and the writeup corpus. The namespace result is the load-bearing one, because it is what lets `conduit` be `verified` rather than `self`. Twenty decisions locked. Nothing built yet; next action is Phase 0. |
