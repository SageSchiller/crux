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
> **State as of 2026-08-20: Phase 6 is complete. All three tracks are built out. Only chain mode (Phase 7) remains.** It lives at `~/projects/crux`, outside the Obsidian vault, same as `waypoint` and `hone`, and it is its own git repository.
>
> **The harness and the whole sift engine are built, across seven artifact families.** Track picker, the marking screen with its two beats and horizontal panning, the seeded fixture builder, scoring, history, help, and honest stubs for the two unbuilt tracks. Families: nmap, web content discovery, `sudo -l`, SMB share enumeration, local enumeration output, listening sockets, and a single HTTP response. `python3 validate.py` is clean with zero warnings, `python3 test.py` is green, `python3 test-tty.py` is green against a real pty, and `./build.sh` produces a `dist/crux.pyz` that runs standalone. The live counts are whatever `validate.py` prints; it is authoritative and cannot drift, so do not keep a table of them here.
>
> **`validate.py --scores` prints the score profile**, which is how `DECOY_WEIGHT` stopped being a guess and how a too-short fixture gets caught.
>
> **The Phase 1 gate was passed on the author's instruction, not by a played session.** Recorded plainly because it is the one thing in this plan that was not verified the way the plan said it would be. If the marking mechanic turns out to want changing, it now has to change against twenty-six scenarios rather than eleven.
>
> **`salvage` is `verified` for real.** crux opens an instrumented service on loopback, writes the broken script to disk, hands the terminal to your editor and then to `python3`, and reads back what actually arrived. Five defect classes are authored, four over HTTP and one over raw TCP. **`validate.py` runs every reference solution and every broken script against a live target**: the solution must land and the broken one must not, which is what proves each exercise is both solvable and actually broken. The whole run takes about 1.5 seconds; `--fast` skips it.
>
> **All ten defect classes are authored and the capstone works.** `salvage-hostile` is the only scenario in crux you can fail by pressing a key: the proof-of-concept contacts an address written into it before it touches the target, crux owns that address, and the run ends there however well the exploit worked. Its broken script **does** land, deliberately, because "working scripts can still be hostile" is the lesson and "broken scripts are broken" is not.
>
> **The spike succeeded and conduit verifies for real.** crux builds a genuine multi-hop network out of unprivileged namespaces, runs a real `sshd` on the pivot, executes your tunnel script in the attacker namespace and probes the path. No sudo, and where the kernel will not allow it the track says so on screen and scores nothing (D14).
>
> **conduit has seven topologies:** local forward, socat relay, reverse forward, dynamic SOCKS, three-hop chain, a blocked-forwarding diagnosis, and a chisel agent gated on the binary. All but the gated one build and verify for real; the gated one skips cleanly with an install pointer (the hone pattern), and `validate.py` and `test.py` both honour that rather than trying to run it.
>
> **Next action: Phase 7, chain mode** (sift the output, salvage the PoC, conduit to the next subnet, as one scenario). It is the only thing left, and it is the reason the three tracks are one program. Nothing else is blocking or half-finished.
>
> **The lesson from Phase 0, and the reason `test-tty.py` exists.** For the whole of the build the space bar did nothing on the marking screen. The decoder produced `Key(' ')` while every screen compared against `parse('SPC')`, so the app's central verb was dead. **Twelve thousand green checks never touched it**, and could not have: a test that builds its input with `parse()` is asking the notation whether it agrees with itself. Driving the real app through a pty found it on the first run. Two permanent things came out of it: the decoder now agrees with the notation for every special key and `test.py` asserts that across the whole set, and `test-tty.py` is kept as a third suite. **The general form is worth remembering: a test that constructs its inputs the same way the code constructs its expectations cannot fail.**
>
> **The name.** Climbing term for the single hardest move on a route, and in plain English the heart of the matter. Chosen 2026-08-20 over `range` (too generic), `SSC` (welds three tracks into the name when a fourth and fifth are already planned), `quarry` and `assay`. The tracks are `sift`, `salvage` and `conduit`; the program name deliberately does not enumerate them.
>
> **The one-line reason this project exists.** Waypoint tells you what to do next given a known state. hone makes you fluent in the tool. Nothing yet drills the two things in between: **producing** that state from a wall of raw output, and **executing** the thing Waypoint just told you to do when the code you found is broken and the host you want is three subnets away. Those are the two places OSCP attempts actually die.
>
> **Environment facts already established on this machine (2026-08-20), do not re-derive:** unprivileged user + network namespaces work (`unprivileged_userns_clone=1`, `max_user_namespaces=254950`), `unshare -Urn --map-root-user` creates a netns and veth pairs with **no sudo**, a sibling process can join a held namespace via `nsenter --net=/proc/PID/ns/net`, `sshd` is present at `/usr/bin/sshd`, and `socat` / `proxychains4` / `ncat` / `gcc` are installed. `chisel` and `ligolo-ng` are **not** installed and `python2` is **not** present. See *Environment findings* below.
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

**Primary user:** the author, preparing for OSCP.
**Secondary user:** anyone handed the file. It must run with no install and no third-party packages, and it must be safe to hand to a stranger, which is what D2 and D7 are for.

**Audience floor:** someone who has done a few HTB boxes should be able to work the first `sift` scenarios and come out noticing things they were previously scrolling past.

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
| D5 | **One program, three tracks, track select on launch.** The program name does not enumerate the tracks. | Same argument as hone's D4: the harness gets written once. The name argument is separate and was the reason `SSC` lost: `proctor` (exam pacing) and `lineage` (AD path reasoning) are already sketched as tracks four and five, and a name that counts to three would have to be wrong or the project would have to stop growing. |
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
| D22 | **A fixture line's id is derived from its content, never from its position.** Added 2026-08-20 (c). | Entries are shuffled per seed (D10), so a positional id would move the key with the seed and make the scenario unsolvable at some seeds. The first content-derived ids truncated to forty characters and three sudo grants under the same long path collided, which would have made marking one line mark all three; ids now carry a CRC over the whole text. `zlib.crc32` and not `hash()`, because string hashing is salted per process and ids would differ between `validate.py` and the app. |

---

## Architecture

Forked from hone (D4), so the shape is already proven:

```
crux/
├── crux/
│   ├── app.py                 track select, session loop, clock (D12, D17)
│   ├── config.py              paths, XDG, capability probe results
│   ├── state.py               JSON state, export/import (D16)
│   ├── scoring.py             precision/recall, decoy penalty, time (D8, D12)
│   ├── screens/               track select, scenario, result, stats
│   ├── ui/                    Text spans, styling, caps detection (D15)
│   ├── targets/               the things crux builds and owns (D2)
│   │   ├── _fixture.py        seeded synthetic output builder (D10)
│   │   ├── mockhttp.py        instrumented HTTP service for salvage
│   │   ├── mocktcp.py         instrumented raw TCP service for salvage
│   │   └── netlab.py          namespace topology supervisor for conduit (D13)
│   └── content/
│       ├── sift/
│       ├── salvage/
│       └── conduit/
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

## Chain mode (Phase 7)

One scenario carried through all three tracks: sift the output to find the lead, salvage the PoC that exploits it, conduit your way from that foothold to the next subnet. This is the reason the three tracks are one program rather than three, and it is the closest thing crux has to a box. Not attempted before all three tracks stand alone.

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

Per-track payload: `sift` carries the fixture spec, the key (line ids that are leads), the decoys worth naming in feedback, and the action choices. `salvage` carries the defect class list, the broken source, the service spec, and the hit condition. `conduit` carries the topology spec and the probe.

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

### Phase 7: chain mode

### Later, not scheduled
`proctor` (24-hour exam pacing, post-mortem over the D12 time data) and `lineage` (offline AD path reasoning over synthetic BloodHound-shaped graphs) as tracks four and five. Both were designed alongside crux and are the reason D5 exists.

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
5. **Should `sift` fixtures ever be *this machine's* real output** (a scan of crux's own loopback sockets, the hone `netlab` trick)? It would raise realism at some cost in determinism. Not needed before Phase 2.

---

## Session log

| Date | What happened |
|---|---|
| 2026-08-20 (h) | **Phase 6 complete: conduit is seven topologies.** Reverse (`-R`), dynamic (`-D` verified through a real SOCKS5 handshake crux speaks itself), a three-hop chain where the second `-L` classically points home, a blocked-forwarding diagnosis that turns on reading "administratively prohibited" as the server refusing rather than the command being wrong, and a `chisel` reverse-SOCKS agent gated on the binary. **`needs`-gating landed as a general feature**: a scenario naming a missing tool greys out with an install pointer and records nothing, and both suites skip it rather than failing. Two bugs found by running the content. The SOCKS probe carried literal `\\x05` bytes that the heredoc turned into real NULs in the source, so it would not compile; rebuilt from `bytes([...])` so the probe body stays pure ASCII and the NULs are made at runtime. And passing that probe to `python3 -c` failed on the embedded NUL a SOCKS request contains, so probes are written to a temp file instead. The blocked and three-hop scenarios also confirmed the value of the starter-must-fail check twice more: both starters are plausible and both genuinely leave the path closed. |
| 2026-08-20 (g) | **Phase 5 complete: the conduit spike succeeded and the engine is built.** Confirmed by building it: a three-host topology unprivileged, `attacker -> target` unreachable while `pivot -> target` works, teardown verified clean after both a normal exit and a `SIGKILL` (namespace count returns to baseline in both), and a real `ssh -L` through a real `sshd` returning the flag. **The planned long-lived supervisor was dropped for a one-shot builder**, which removed the control protocol, the tty hand-off into a user namespace, and the whole class of teardown problems in one decision. Six separate obstacles had to be cleared to run `sshd` unprivileged; all are written up in the module docstring so nobody re-derives them. **Two real bugs found by running content rather than reading it.** A backgrounded process in a tunnel script inherits the output pipe and holds it open, so `subprocess.run(capture_output=True)` waited for an EOF that never came and every failed attempt cost a 45-second timeout instead of a two-second answer; output goes to a file now. And the first relay scenario shipped a starter that **already worked**, because the defect it was built around (backgrounding the local ssh kills the remote command) turned out not to be a defect at all; the new `check_conduit_runs` caught it immediately, and the scenario now turns on a `bind=127.0.0.1` that puts the relay on the pivot own loopback. |
| 2026-08-20 (f) | **Phase 4 complete: all ten salvage defect classes, ending on the capstone.** Classes 6 to 10 authored; `MockTcp` gained length framing (recording only the framed body, so a miscounted header truncates for real); `SalvageBody` gained a trap sink for D19. **The capstone is the only scenario in crux you can fail by pressing a key**, and its broken script deliberately *works*: anything that made it fail at the exploit too would let a student conclude the lesson is "broken scripts are broken". `validate.py` grades trap scenarios on the trap rather than on the exploit, and asserts that modules a scenario needs absent really are, because `requests` turned out to be installed here and a scenario premised on its absence would have passed silently and behaved differently on a Kali box; `pwntools` is used instead, with the guard. **Two defects found and fixed in the harness, both of which had been shipping since earlier phases.** The result screens were silently truncating the debrief on a 24-row terminal, which is the height backstop working as designed and the worst possible thing for it to eat, so there is now a `ScrollScreen` base and the two result screens, the stub and help all use it. And a structural check written for the capstone failed the reference solution for still *defining* the beacon function it never calls; whether the beacon fires is decided by running it, not by searching the text. |
| 2026-08-20 (e) | **Phase 3 complete: the salvage engine runs, five defect classes authored.** `_hits.py` carries the shared `Request`, `Requirement` and `HitRecord`; `mockhttp.py` and `mocktcp.py` are the two targets and expose the same interface. The screen hands the terminal to `$EDITOR` and to `python3` and takes it back, which is the existing suspend/resume path put to its real use. Content is one scenario per class: Python 2 idioms, a hardcoded callback from the author lab, an endpoint moved between minor versions, a skipped protocol handshake, and a payload encoded twice. **`validate.py` now executes every reference solution and every broken script against a live target** and requires the first to land and the second to fail; the whole suite runs in about 1.5s. **Three bugs, each found by a different suite, and each a real defect rather than a bad assertion.** The TCP target stopped reading at the first newline, so the two-line handshake scenario scored its reference solution *lower* than the broken script it was meant to fix, which the new validate check caught immediately. The handover called `input()` unconditionally, so `test.py` hung for two minutes on a stdin nobody was typing into: the pause only makes sense when there was a terminal to give back. And the TCP target recorded on connection close rather than before replying, so a client could read `OK` and ask for the verdict before the record existed, which is exactly what the screen does the moment the subprocess exits. Recording before replying removes the race entirely. |
| 2026-08-20 (d) | **Phase 2 complete; the sift track is done at 26 scenarios across seven families.** New builders: `SmbShares` (in two real output shapes), `PeasChunk`, `NetstatDump`, `LdapUsers`, `HttpResponse`. New families: SMB share enumeration, local enumeration output, listening sockets, directory dumps, and a short HTTP family. Six scenarios now have no lead at all (D9), and `test.py` asserts they stay under half the content so the app does not train the opposite reflex. **Three checks paid for themselves on their first run.** The provenance audit (new, and the plan asked for it) found that three of the first eleven scenarios cited writeups that do not exist, and one was wrong in a way that mattered: the box it should have cited records `/dev` returning **403**, not the 200 the scenario had been authored around, so the content was corrected as well as the citation. The score profile (`validate.py --scores`) found that the `netstat` fixtures were nine lines long, so marking every line scored 31 against the 5 it scores on a realistic screen; the fix was more realistic output, not a harsher scorer. And it found `sift-peas-suid` had no authored decoys at all, so its wrong answers named lines the scorer never charged for. **`DECOY_WEIGHT` is now measured rather than guessed:** at 2.0 greedy marking averages 11 and never exceeds 20; at 3.0 the greedy average only moves to 10 while chasing one decoy on a two-lead screen drops to 57 against 67 for missing a lead, inverting the relationship the scorer exists to express. 2.0 stays. Also closed a real test gap: `test.py` was render-testing two scenarios out of twenty-six, and content is exactly where non-ASCII and overlong lines get introduced. |
| 2026-08-20 (c) | **Phase 1 built.** `crux/targets/_fixture.py` is the seeded builder of D10, with three families: `NmapScan` (with and without `-sV`, and NSE script blocks as the real source of bulk), `FeroxRun`, and `SudoL`. `MarkBody` now holds a fixture rather than literal lines and materialises a fresh screen per attempt; the seed rides on the recorded attempt so a run can be reproduced, and `--seed` pins it. Eleven scenarios authored across the three families, all with real provenance into the PEN-200 writeups and real Waypoint node ids, two of them no-lead (D9). The Phase 0 smoke scenario is deleted. **Three things were discovered by doing rather than planning.** Authoring the domain-controller scan showed that real output is wider than a terminal and the tell is often at the end of the line, which produced D21 and horizontal panning; shortening the line to fit was rejected because a fixture that prints what nmap does not is worthless. The new "key is stable across seeds" check in `validate.py`, written for the defect class the seeded builder introduces, instead caught a different real bug on its first run: three nagiosxi sudo grants shared their first forty characters, so they shared an id, so marking one would have marked all three. That produced D22. And the first size-anomaly scenario contained no anomaly, because noise 200s were drawn from a wide random range and nothing clustered; page sizes now cluster the way pages cut from one template do. `validate.py` clean with **zero warnings**, `test.py` green, `test-tty.py` green. |
| 2026-08-20 (b) | **Phase 0 landed.** `keys.py`, `term.py`, `render.py`, `theme.py` and the screen contract were forked from hone per D4; `config`, `clock`, `model`, `scoring`, `state`, `loader`, `session`, `app` and six screens are new. The scoring arithmetic of D8 and D9 was checked against real numbers before anything was built on it: marking everything on a forty-line screen scores 9, and missing a lead costs exactly what chasing a decoy costs. One smoke scenario per track, with `salvage` and `conduit` carrying honest `self`-tier stubs that record nothing rather than pretending. **Two bugs, both found by tests that did not exist an hour earlier.** The stopwatch was being paused when the marking screen handed it to the act beat, so beat two's time silently vanished from history, which D12 cannot tolerate; the walkthrough test caught it. Then the space bar turned out to have never worked at all, which no unit test could see: `test-tty.py` was written to drive the real app through a pty and found it on the first run, and it is kept as a permanent third suite. The decoder now agrees with the notation for every special key and `test.py` asserts it. `validate.py` clean with one true warning (the smoke fixture has no provenance, which it does not), `test.py` green, `test-tty.py` green, `dist/crux.pyz` builds and finds its content inside the archive. |
| 2026-08-20 | **Project scoped and named.** Came out of a conversation about what to build for OSCP prep beyond Waypoint, hone, and the writeups. Six candidates were sketched; three were selected and bundled into one program on the argument that they are consecutive stages of the same engagement rather than three unrelated drills. Name settled as `crux` after `range`, `SSC`, `quarry` and `assay` were considered and rejected for the reasons in the START HERE block. Feasibility probes run before writing anything: unprivileged namespaces, `nsenter` join, `sshd`, and the writeup corpus. The namespace result is the load-bearing one, because it is what lets `conduit` be `verified` rather than `self`. Twenty decisions locked. Nothing built yet; next action is Phase 0. |
