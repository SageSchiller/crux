#!/usr/bin/env python3
"""Structural checks over content and the harness invariants.

Errors exit non-zero. Warnings do not, but they are the place scaffolding goes
to be noticed: a Phase 0 smoke scenario sitting beside real content is a
warning, because the failure mode it prevents is placeholder content quietly
becoming canon.

`validate.py` is authoritative on counts. Do not maintain a table of them in
the plan; print them here instead, where they cannot drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crux import render as R
from crux.config import (CHAIN, COMPOSITE, EXIT_CHORD, PROCTOR, SECTIONS,
                         TIERS, TRACKS, vault_dir)
from crux.loader import load
from crux.model import (ChainBody, ConduitBody, LINE_KINDS, LineageBody,
                        MarkBody, SalvageBody, Scenario, SittingBody,
                        Stage, StubBody, missing_needs, roles)
from crux import lineage as LN
from crux import pacing
from crux.scoring import DECOY_WEIGHT, score_marks
from crux.state import State
from crux.screens import Screen
from crux.version import VERSION

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def check_registry(reg) -> None:
    for e in reg.errors:
        err(f'load: {e}')
    ids = [s.id for s in reg.scenarios]
    if len(ids) != len(set(ids)):
        err('duplicate scenario ids across tracks')
    for name in SECTIONS:
        if name not in reg.tracks:
            err(f'section {name} did not load at all')


#: The engagement order, and the only order a chain's stages may take: find
#: the lead, land the exploit, reach the next host, then escalate through the
#: domain. A chain is a prefix of this, so the two original engagements are the
#: three-stage form and an Active Directory one can carry the fourth.
CHAIN_ORDER = ('sift', 'salvage', 'conduit', 'lineage')


def check_chain_body(s: Scenario) -> None:
    """A chain must be exactly the three tracks in engagement order, each leg
    carrying a body its own engine can run.

    The order matters: the fiction is find, then land, then reach, and a chain
    that ran salvage before sift would be teaching the wrong sequence. Each
    leg's body is validated by the same checks its standalone track uses, so a
    broken exploit inside a chain is caught exactly as one in the salvage
    track would be.
    """
    b: ChainBody = s.body
    if s.tier != 'verified':
        err(f'{s.id}: a chain is verified, not {s.tier!r}')
    tracks = tuple(st.track for st in b.stages)
    # A chain is the first N stages of the engagement order: find, land, reach,
    # and now escalate. The prefix rule keeps the fiction a pipeline (a chain
    # that ran salvage before sift would teach the wrong sequence) while
    # letting an Active Directory engagement carry a fourth `lineage` stage
    # where the domain half of the exam actually ends. Three or four stages;
    # a two-stage chain is not enough to be an engagement.
    if tracks != CHAIN_ORDER[:len(tracks)] or not 3 <= len(tracks) <= 4:
        err(f'{s.id}: stages are {tracks}, must be a prefix of '
            f'{CHAIN_ORDER} of length 3 or 4 (find, land, reach, escalate)')
    if not b.brief.strip():
        err(f'{s.id}: no engagement brief')
    for st in b.stages:
        if not st.bridge.strip():
            warn(f'{s.id}: the {st.track} stage has no bridge text, so the '
                 'engagement has no story between legs')
        sub = Scenario(id=f'{s.id}:{st.track}', track=st.track,
                       title=st.title or s.title,
                       tier=('graded' if st.track in ('sift', 'lineage')
                             else 'verified'),
                       body=st.body, needs=st.needs, source=s.source)
        # A leg inherits the chain's source and waypoint, so silence the
        # per-scenario provenance warnings the standalone check would emit:
        # the engagement is the unit of provenance, not each leg.
        pre_warn = len(WARNINGS)
        if isinstance(st.body, MarkBody):
            check_mark_body(sub)
        elif isinstance(st.body, SalvageBody):
            check_salvage_body(sub)
        elif isinstance(st.body, ConduitBody):
            check_conduit_body(sub)
        elif isinstance(st.body, LineageBody):
            check_lineage_body(sub)
        else:
            err(f'{s.id}: the {st.track} stage body is a '
                f'{type(st.body).__name__}, not the {st.track} engine body')
        WARNINGS[:] = [w for w in WARNINGS
                       if not (WARNINGS.index(w) >= pre_warn
                               and 'no Waypoint node' in w
                               and f'{s.id}:{st.track}' in w)]


def check_scenario(s: Scenario) -> None:
    if s.track not in SECTIONS:
        err(f'{s.id}: unknown track {s.track!r}')
    if s.tier not in TIERS:
        err(f'{s.id}: unknown tier {s.tier!r}')
    if not s.title.strip():
        err(f'{s.id}: empty title')
    if s.body is None:
        err(f'{s.id}: no body')
        return

    if isinstance(s.body, MarkBody):
        check_mark_body(s)
    elif isinstance(s.body, SalvageBody):
        check_salvage_body(s)
    elif isinstance(s.body, ConduitBody):
        check_conduit_body(s)
    elif isinstance(s.body, ChainBody):
        check_chain_body(s)
    elif isinstance(s.body, SittingBody):
        check_sitting_body(s)
    elif isinstance(s.body, LineageBody):
        check_lineage_body(s)
    elif isinstance(s.body, StubBody):
        if s.tier != 'self':
            err(f'{s.id}: a stub must be self tier, not {s.tier!r} '
                f'(crux D6: never claim a check that is not happening)')
        if not s.body.phase:
            err(f'{s.id}: a stub must name the phase that builds it')
    else:
        err(f'{s.id}: unknown body type {type(s.body).__name__}')


def check_salvage_body(s: Scenario) -> None:
    """Structure only. The solution is actually run by `check_salvage_runs`."""
    b: SalvageBody = s.body
    if s.tier != 'verified':
        err(f'{s.id}: salvage is verified, not {s.tier!r} (crux D6: crux is '
            'the target, so it is not taking anybody word for this)')
    if b.kind not in ('http', 'tcp'):
        err(f'{s.id}: unknown target kind {b.kind!r}')
    if not b.requirements:
        err(f'{s.id}: no requirements, so nothing could ever land')
    if not b.brief.strip():
        err(f'{s.id}: no brief')
    if not b.defects:
        warn(f'{s.id}: names no defect classes, so the result screen cannot '
             'say what was wrong with the original')
    if b.broken == b.solution:
        err(f'{s.id}: the broken script and the solution are identical')
    if b.trap:
        if '{{SINK}}' not in b.broken:
            err(f'{s.id}: has a trap but the script never contacts it')
        # Whether the solution still *fires* the beacon is decided by running
        # it, in `check_salvage_runs`, and not by looking for a call in the
        # text. The first version of this check searched for the function name
        # and failed the solution because it still defines the function it
        # never calls, which is a perfectly legitimate minimal fix.
    for mod in b.needs_absent:
        try:
            __import__(mod)
        except ImportError:
            continue
        err(f'{s.id}: needs {mod!r} to be absent for its defect to bite, and '
            f'it is importable here. The broken script would work and the '
            f'scenario would teach nothing. Either uninstall it for this '
            f'check or re-author the scenario')
    if '{{PORT}}' in b.broken and b.kind == 'http':
        warn(f'{s.id}: an http scenario substitutes PORT rather than URL')
    for q in b.requirements:
        if not q.hint.strip():
            warn(f'{s.id}: requirement {q.name!r} has no hint, so a student '
                 'who misses it is told only that they missed it')
    if not s.source:
        warn(f'{s.id}: no provenance (crux D11)')


def check_conduit_body(s: Scenario) -> None:
    b: ConduitBody = s.body
    if s.tier != 'verified':
        err(f'{s.id}: conduit is verified, not {s.tier!r}')
    if b.starter == b.solution:
        err(f'{s.id}: the starter and the solution are identical')
    if not b.brief.strip():
        err(f'{s.id}: no brief')
    topo = b.topology
    if not getattr(topo, 'probes', ()):
        err(f'{s.id}: no probes, so nothing could ever be verified')
    if not getattr(topo, 'negative', ()):
        warn(f'{s.id}: no negative probe. Without one, a topology that was '
             'reachable all along would score as a pass and nobody would '
             'ever find out')
    if not s.source:
        warn(f'{s.id}: no provenance (crux D11)')


def check_conduit_runs(reg) -> None:
    """Build every topology for real, twice.

    The solution must open the path and **the starter must not**. That second
    half is not symmetry for its own sake: the first version of the relay
    scenario shipped a starter that already worked, because the defect it was
    built around turned out not to be a defect. Reading the script would never
    have told anybody. Running it did, immediately.

    About four seconds per run, so roughly fifteen for the track. `--fast`
    skips it.
    """
    import tempfile

    from crux.targets.netns import capability, prepare_assets, run_attempt

    conduits = [s for s in reg.scenarios if isinstance(s.body, ConduitBody)]
    if not conduits:
        return
    usable, why = capability()
    if not usable:
        print(f'  note  conduit not verified here: {why} (crux D14)')
        return

    work = Path(tempfile.mkdtemp(prefix='crux-validate-conduit-'))
    assets = prepare_assets(work / 'assets')
    for s in conduits:
        miss = missing_needs(s)
        if miss:
            print(f'  note  {s.id} not run: needs {", ".join(miss)}')
            continue
        b: ConduitBody = s.body
        for label, src, want in (('solution', b.solution, True),
                                 ('starter', b.starter, False)):
            path = work / b.filename
            path.write_text(b.render(src, str(assets)), encoding='utf-8')
            r = run_attempt(b.topology, path, assets, b.settle)
            if r.error and want:
                err(f'{s.id}: building the topology failed: {r.error}')
                continue
            if want and not r.ok:
                err(f'{s.id}: the reference solution does not open the path '
                    f'({r.met}/{r.total}: {r.detail}), so the scenario is '
                    'unsolvable')
            if not want and r.ok:
                err(f'{s.id}: the STARTER script already works, so the '
                    'scenario teaches nothing')


def check_chain_runs(reg) -> None:
    """Run each chain's salvage and conduit legs for real, like the standalone
    tracks. A chain is only as trustworthy as its legs, and a leg that does
    not land makes the engagement unwinnable at exactly the point a real box
    would stop you."""
    import subprocess
    import tempfile

    from crux.targets.mockhttp import MockHttp
    from crux.targets.mocktcp import MockTcp
    from crux.targets.netns import (capability, prepare_assets, run_attempt)

    lin = [s for s in reg.scenarios if isinstance(s.body, LineageBody)]
    if lin:
        graphs = [s.body.canonical() for s in lin]
        nodes = sum(len(g.nodes) for g in graphs)
        rights = sum(len(g.edges) for g in graphs)
        culs = sum(len(_culdesacs(g)) for g in graphs)
        print(f'  lineage   {len(lin)} collection(s), {nodes} principals, '
              f'{rights} rights, {culs} branch(es) that go nowhere')
        print('  routes    every objective reachable, cheapest route stable '
              'across all seeds')
    sits = [s for s in reg.scenarios if isinstance(s.body, SittingBody)]
    if sits:
        legs = sum(len(s.body.slots) for s in sits)
        budget = sum(s.body.budget for s in sits)
        print(f'  proctor   {len(sits)} sitting(s), {legs} leg(s), '
              f'{budget / 60:.0f} minutes of budget')
        print('  slots     every slot fills on a fresh install and on a '
              'full history')
    chains = [s for s in reg.scenarios if isinstance(s.body, ChainBody)]
    if not chains:
        return
    ns_ok, _ = capability()
    assets = None
    for s in chains:
        for st in s.body.stages:
            if isinstance(st.body, SalvageBody):
                b = st.body
                target = (MockTcp(b.requirements, banner=b.banner)
                          if b.kind == 'tcp'
                          else MockHttp(b.requirements, route=b.route,
                                        reject_code=b.reject_code,
                                        reject_message=b.reject_message))
                with target:
                    work = Path(tempfile.mkdtemp(prefix='crux-chain-'))
                    path = work / b.filename
                    path.write_text(b.render(b.solution,
                                             getattr(target, 'url', ''),
                                             target.port))
                    try:
                        subprocess.run([sys.executable, str(path)],
                                       cwd=str(work), capture_output=True,
                                       timeout=30)
                    except subprocess.TimeoutExpired:
                        err(f'{s.id}: the salvage leg did not finish')
                        continue
                    if not target.verdict()[0]:
                        err(f'{s.id}: the salvage leg solution does not land, '
                            'so the engagement cannot be completed')

                # And the broken script must NOT land, or the leg teaches
                # nothing. Checked separately against a fresh target, because
                # the first one has the solution's hit on its record. This is
                # the same standard the standalone tracks are held to, and it
                # was missing here.
                broken_target = (
                    MockTcp(b.requirements, banner=b.banner)
                    if b.kind == 'tcp'
                    else MockHttp(b.requirements, route=b.route,
                                  reject_code=b.reject_code,
                                  reject_message=b.reject_message))
                with broken_target:
                    work = Path(tempfile.mkdtemp(prefix='crux-chain-b-'))
                    path = work / b.filename
                    path.write_text(b.render(
                        b.broken, getattr(broken_target, 'url', ''),
                        broken_target.port))
                    try:
                        subprocess.run([sys.executable, str(path)],
                                       cwd=str(work), capture_output=True,
                                       timeout=30)
                    except subprocess.TimeoutExpired:
                        pass
                    if broken_target.verdict()[0]:
                        err(f'{s.id}: the salvage leg broken script already '
                            'lands, so that stage teaches nothing')
            elif isinstance(st.body, ConduitBody):
                if not ns_ok or missing_needs(
                        Scenario(id='x', track='conduit', title='x', tier='verified',
                                 body=st.body, needs=st.needs)):
                    print(f'  note  {s.id} conduit leg not run')
                    continue
                if assets is None:
                    assets = prepare_assets(
                        Path(tempfile.mkdtemp(prefix='crux-chain-a-'))
                        / 'assets')
                work = Path(tempfile.mkdtemp(prefix='crux-chain-c-'))
                path = work / st.body.filename
                path.write_text(st.body.render(st.body.solution, str(assets)))
                r = run_attempt(st.body.topology, path, assets, st.body.settle)
                if not r.ok:
                    err(f'{s.id}: the conduit leg solution does not open the '
                        f'path ({r.detail or r.error})')
                path.write_text(st.body.render(st.body.starter, str(assets)))
                rb = run_attempt(st.body.topology, path, assets, st.body.settle)
                if rb.ok:
                    err(f'{s.id}: the conduit leg starter already opens the '
                        'path, so that stage teaches nothing')


def check_salvage_runs(reg) -> None:
    """Run every reference solution against a real target, and every broken
    script too.

    **This is the check that makes the track trustworthy.** A salvage scenario
    can fail in two directions and both ship silently: a solution that does
    not actually land makes the scenario unsolvable, and a broken script that
    lands anyway makes it pointless. Neither is visible by reading the source.
    So both are executed, against the same mock service the student will face.

    It found one on its first run: the TCP target stopped reading at the first
    newline, so the handshake scenario reference solution scored *lower* than
    the broken script it was supposed to fix.
    """
    import subprocess
    import tempfile

    from crux.targets.mockhttp import MockHttp
    from crux.targets.mocktcp import MockTcp

    for s in reg.scenarios:
        b = s.body
        if not isinstance(b, SalvageBody):
            continue
        for label, src, want in (('solution', b.solution, True),
                                 ('broken', b.broken, False)):
            target = (MockTcp(b.requirements, banner=b.banner,
                              framing=b.framing) if b.kind == 'tcp'
                      else MockHttp(b.requirements, route=b.route,
                                    reject_code=b.reject_code,
                                    reject_message=b.reject_message))
            sink = MockHttp(b.trap, route='/feed') if b.trap else None
            with target:
                if sink is not None:
                    sink.start()
                try:
                    work = Path(tempfile.mkdtemp(prefix='crux-validate-'))
                    path = work / b.filename
                    path.write_text(
                        b.render(src, getattr(target, 'url', ''), target.port,
                                 sink.url if sink is not None else ''),
                        encoding='utf-8')
                    try:
                        subprocess.run([sys.executable, str(path)],
                                       cwd=str(work), capture_output=True,
                                       timeout=30)
                    except subprocess.TimeoutExpired:
                        err(f'{s.id}: the {label} script did not finish in 30s')
                        continue
                    landed, detail, met = target.verdict()
                    tripped = sink is not None and sink.record.count > 0

                    # A trap scenario is graded on the trap, not on the
                    # exploit. Its broken script is *supposed* to work, which
                    # is exactly why anybody would run it unread.
                    if b.trap:
                        if want and tripped:
                            err(f'{s.id}: the reference solution still trips '
                                'the trap')
                        if want and not landed:
                            err(f'{s.id}: the reference solution does not land')
                        if not want and not tripped:
                            err(f'{s.id}: the BROKEN script does not trip the '
                                'trap, so the capstone tests nothing')
                        continue

                    if landed and not want:
                        err(f'{s.id}: the BROKEN script lands, so the exercise '
                            'teaches nothing')
                    elif want and not landed:
                        err(f'{s.id}: the reference solution does not land '
                            f'({met}/{len(b.requirements)}: {detail}), so the '
                            'scenario is unsolvable')
                finally:
                    if sink is not None:
                        sink.stop()


#: Seeds every fixture is built at. Not a round number of consecutive
#: integers on purpose: a builder that keys off `seed % something` would pass
#: 0..5 and fail in the wild.
PROBE_SEEDS = (0, 1, 7, 42, 1000, 65535, 99991, 2 ** 31 - 1)


def check_mark_body(s: Scenario) -> None:
    b: MarkBody = s.body
    if not b.prompt.strip():
        err(f'{s.id}: no prompt')
    if s.tier != 'graded':
        err(f'{s.id}: a marking scenario is graded, not {s.tier!r}')

    correct = [a for a in b.actions if a.correct]
    if b.actions:
        if len(correct) != 1:
            err(f'{s.id}: {len(correct)} correct actions, need exactly 1')
        for a in b.actions:
            if not a.why.strip():
                warn(f'{s.id}: action {a.text[:30]!r} explains nothing; the '
                     'wrong options are where the reasoning lives')
    if not s.source:
        warn(f'{s.id}: no provenance (crux D11)')
    if not s.waypoint:
        warn(f'{s.id}: no Waypoint node (crux D11)')

    # The fixture must build at every seed, and the key must survive all of
    # them. This is the defect class the seeded builder introduces: a lead
    # that is present at seed 0 and absent at seed 99991 makes the scenario
    # silently unsolvable for whoever draws that seed, and nobody would ever
    # reproduce the report. Checked here rather than hoped for.
    first_leads: frozenset[str] | None = None
    for seed in PROBE_SEEDS:
        try:
            lines = b.build(seed)
        except Exception as e:                       # noqa: BLE001
            err(f'{s.id}: fixture raised at seed {seed}: '
                f'{e.__class__.__name__}: {e}')
            return
        if not lines:
            err(f'{s.id}: fixture produced no lines at seed {seed}')
            return

        ids = [ln.id for ln in lines]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            err(f'{s.id}: duplicate line ids at seed {seed}: {dupes}')
        for ln in lines:
            if ln.kind not in LINE_KINDS:
                err(f'{s.id}: line {ln.id!r} has bad kind {ln.kind!r}')

        for ln in lines:
            if ln.kind in ('lead', 'decoy') and not ln.why.strip():
                warn(f'{s.id}: {ln.kind} {ln.id!r} explains nothing. The score '
                     'tells a student they missed or chased it; only `why` '
                     'tells them what it meant')
                break

        leads, decoys = roles(lines)
        if first_leads is None:
            first_leads = leads
        elif leads != first_leads:
            err(f'{s.id}: the key moves with the seed. At seed {seed} the '
                f'leads are {sorted(leads)}, at seed {PROBE_SEEDS[0]} they '
                f'were {sorted(first_leads)}')
        if not decoys:
            warn(f'{s.id}: no decoys. Nothing on this screen is authored to '
                 'tempt, so chasing costs the same as a stray mark and the '
                 'wrong answers name lines the scorer does not charge for')


#: A lineage graph where always taking the cheapest visible move scores at
#: least this has no decision in it. Same argument as `GREEDY_CEILING` for
#: sift: if the greedy strategy wins, the exercise is a formality and the fix
#: is a better graph, never a harsher scorer.
GREEDY_WALK_CEILING = 90.0

#: What a lineage scenario may claim to teach, and what proves each claim.
TEACHES = ('cost', 'reach', 'nesting', 'quiet', '')


def _forward(built, node_id: str) -> set[str]:
    """Everything reachable from one principal, following every right."""
    seen, frontier = {node_id}, [node_id]
    out = {}
    for e in built.edges:
        out.setdefault(e.src, []).append(e)
    while frontier:
        for e in out.get(frontier.pop(), ()):
            if e.dst not in seen:
                seen.add(e.dst)
                frontier.append(e.dst)
    return seen


def _culdesacs(built) -> list:
    """Purchasable branches that cannot reach the objective, however far you
    follow them. The graph equivalent of a sift decoy."""
    return [e for e in LN.available(built, built.owned)
            if built.objective not in _forward(built, e.dst)]


def _noisy_alternative(built, best) -> tuple:
    """The cheapest arriving route that writes to the directory, if one exists.

    Asked per write edge via `cheapest_through`, which forces a route through
    that edge without deleting anything, so a loud route that shares its tail
    with the quiet one is still found. Returns the cheapest such route, or a
    falsey path, so the caller can also check the loud route is a real
    temptation (close in cost) rather than a technicality three times the
    price.
    """
    routes = [LN.cheapest_through(built, e) for e in built.edges
              if LN.writes(e.kind)]
    routes = [r for r in routes if r.reachable]
    return min(routes, key=lambda r: r.cost) if routes else None


def _greedy(built, budget: int):
    """Always take the cheapest visible move. Returns (arrived, spent).

    The strategy a student falls into when they do not read the collection,
    and the one the content has to beat. It is not a solver: the tie-break is
    whatever order `available` returns, which the seed moves, so this is
    measured across seeds rather than asserted at one.
    """
    owned = set(built.owned)
    spent = 0
    while True:
        if built.objective in LN.closure(owned, built.edges):
            return True, spent
        moves = [e for e in LN.available(built, owned)
                 if LN.cost_of(e.kind) <= budget - spent]
        if not moves:
            return False, spent
        pick = moves[0]
        owned.add(pick.dst)
        spent += LN.cost_of(pick.kind)


def check_lineage_body(s: Scenario) -> None:
    """A lineage graph must be solvable, stable, and actually teach what it
    says it teaches.

    The last of those is the one worth having. `teaches` is a claim about the
    shape of the graph -- that the cheapest route is not the shortest, that
    there is a branch which goes nowhere, that you start holding more than you
    were told -- and a claim in content that nothing recomputes is a claim that
    goes stale the first time an edge moves. Every one of them is proved here
    against the built graph.
    """
    b: LineageBody = s.body
    if s.tier != 'graded':
        err(f'{s.id}: a lineage scenario is graded, not {s.tier!r}')
    if not b.brief.strip():
        err(f'{s.id}: no brief')
    if b.teaches not in TEACHES:
        err(f'{s.id}: teaches={b.teaches!r} is not one of {TEACHES}')
    if b.tutorial and b.teaches:
        err(f'{s.id}: a tutorial makes no teaches claim; it demonstrates the '
            f'mechanic rather than a graph property')
    if not b.debrief.strip():
        warn(f'{s.id}: no debrief; the route is only half the lesson')

    first_key = None
    greedy_scores = []
    for seed in PROBE_SEEDS:
        try:
            built = b.build(seed)
        except Exception as e:                            # noqa: BLE001
            err(f'{s.id}: graph raised at seed {seed}: '
                f'{e.__class__.__name__}: {e}')
            return

        ids = [n.id for n in built.nodes]
        known = set(ids)
        # Structure is authored and does not vary, so it is checked once.
        # Reporting a bad edge kind eight times, once per seed, buries the
        # seven other things wrong with a broken graph.
        if seed == PROBE_SEEDS[0]:
            if len(ids) != len(set(ids)):
                err(f'{s.id}: duplicate node ids')
            for e in built.edges:
                if e.src not in known or e.dst not in known:
                    err(f'{s.id}: right {e.id} points at a principal that is '
                        f'not in the collection')
                if e.kind not in LN.EDGE_COST:
                    err(f'{s.id}: right {e.id} has kind {e.kind!r}, which has '
                        f'no price, so it would silently cost 1')
        if built.objective not in known:
            err(f'{s.id}: the objective {built.objective!r} is not in the '
                f'collection')
            return

        start = LN.closure(built.owned, built.edges)
        if built.objective in start:
            err(f'{s.id}: you already hold the objective at seed {seed}')
            return

        best = LN.cheapest(built)
        if not best.reachable:
            err(f'{s.id}: the objective cannot be reached at seed {seed}')
            return
        if best.cost <= 0:
            err(f'{s.id}: the objective is free to reach, so there is no '
                f'decision in this graph')

        # The key must not move with the seed, exactly as a sift key must not.
        key = tuple(sorted(e.id for e in best.edges))
        if first_key is None:
            first_key = key
        elif key != first_key:
            err(f'{s.id}: the cheapest route moves with the seed. At {seed} it '
                f'is {list(key)}, at {PROBE_SEEDS[0]} it was '
                f'{list(first_key)}')

        budget = LN.budget_for(best.cost)
        if budget < best.cost:
            err(f'{s.id}: the budget {budget} cannot pay for the cheapest '
                f'route at {best.cost}')

        arrived, spent = _greedy(built, budget)
        score = LN.score_walk(built, [], arrived, best.cost, budget)
        greedy_scores.append(
            round(min(100.0, 100.0 * best.cost / spent), 1) if (arrived and spent)
            else 0.0)

        if seed == PROBE_SEEDS[0] and not b.tutorial:
            _check_teaches(s, built, best)

        for e in best.edges:
            if e.kind not in LN.FREE and not e.why.strip():
                warn(f'{s.id}: the cheapest route uses {e.kind} and says '
                     'nothing about why; the score tells a student the route '
                     'cost more than it had to, and only `why` says what made '
                     'it expensive')
                break

    # A `quiet` scenario is exempt from the greedy-cost ceiling on purpose:
    # its two routes cost the same by design, so a strategy that reads only
    # cost is *meant* to score full marks on it. The reading it trains is
    # noise, which the cost-greedy simulator cannot see, and the real check
    # for it is `_noisy_alternative` above. Applying the cost ceiling here
    # would demand a graph the scenario is specifically built not to be.
    # The tutorial is exempt from the drill-quality warnings on purpose (see
    # LineageBody): it teaches the mechanic by being trivial, so a greedy
    # player winning it and its having no dead end are the point, not defects.
    # A `quiet` scenario is also exempt from the greedy-cost ceiling: its two
    # routes cost the same by design, so a cost-only strategy is meant to score
    # full marks and the reading it trains is noise, which the cost simulator
    # cannot see.
    if greedy_scores and not b.tutorial and b.teaches != 'quiet':
        mean = sum(greedy_scores) / len(greedy_scores)
        if mean >= GREEDY_WALK_CEILING:
            warn(f'{s.id}: always taking the cheapest visible move averages '
                 f'{mean:.0f} across seeds, over the '
                 f'{GREEDY_WALK_CEILING:.0f} ceiling. There is no reading to '
                 f'do in this graph; add a branch worth getting wrong rather '
                 f'than harshening the scorer')

    if not b.tutorial and not _culdesacs(b.canonical()):
        warn(f'{s.id}: no branch out of what you hold fails to reach the '
             'objective, so nothing here is worth getting wrong')

    # At most one tutorial in the track: two would mean the mechanic is being
    # taught twice and drilled once less.
    if b.tutorial:
        others = [x for x in _reg_lineage_tutorials() if x != s.id]
        if others:
            err(f'{s.id}: more than one lineage tutorial ({[s.id] + others}); '
                f'the track teaches the mechanic once')


def _reg_lineage_tutorials() -> list:
    from crux.loader import load
    from crux.model import LineageBody as _LB
    return [x.id for x in load().scenarios
            if isinstance(x.body, _LB) and x.body.tutorial]


def _check_teaches(s: Scenario, built, best) -> None:
    """Prove the scenario's `teaches` claim against the graph it built."""
    b: LineageBody = s.body
    if b.teaches == 'cost':
        hops = LN.shortest(built)
        if not (hops.reachable and hops.cost > best.cost):
            err(f'{s.id}: teaches="cost", but the fewest-edges route costs '
                f'{hops.cost} against the cheapest at {best.cost}. There is '
                f'no gap to teach')
    elif b.teaches == 'reach':
        culs = [e for e in _culdesacs(built) if LN.cost_of(e.kind) >= 2]
        if not culs:
            err(f'{s.id}: teaches="reach", but every branch out of what you '
                f'hold reaches the objective, or the ones that do not are '
                f'free to enter')
    elif b.teaches == 'nesting':
        start = LN.closure(built.owned, built.edges)
        extra = len(start) - len(set(built.owned))
        if extra < 2:
            err(f'{s.id}: teaches="nesting", but you start holding only '
                f'{extra} principal(s) beyond what you were handed')
    elif b.teaches == 'quiet':
        loud = [e.kind for e in best.edges if LN.writes(e.kind)]
        if loud:
            err(f'{s.id}: teaches="quiet", but the cheapest route itself '
                f'writes to the directory: {loud}')
        noisy = _noisy_alternative(built, best)
        if not noisy:
            err(f'{s.id}: teaches="quiet", but no route that arrives writes '
                f'anything, so there is no quieter choice to make')
        elif noisy.cost > LN.budget_for(best.cost):
            err(f'{s.id}: teaches="quiet", but the cheapest writing route '
                f'costs {noisy.cost}, past the budget of '
                f'{LN.budget_for(best.cost)}, so it is not a real temptation')


#: A leg with less clock than this is not an exercise, it is a formality.
#: Nothing in the content is near it; the floor exists so a budget typo cannot
#: ship a sitting whose salvage leg is entitled to forty seconds.
MIN_ALLOCATION = 90.0


def check_sitting_body(s: Scenario) -> None:
    """A sitting schedules other tracks, so most of what can be wrong with one
    is arithmetic rather than content.

    The check that matters is the last one. A sitting whose pass mark can only
    be reached by landing **every** leg has no triage in it: walking away is
    then strictly wrong, and the one verb the track adds is a trap rather than
    a skill. That is a design error rather than a typo, and it is invisible
    until someone works out the arithmetic, so it is worked out here.
    """
    import math
    b: SittingBody = s.body
    if s.tier != 'graded':
        err(f'{s.id}: a sitting is graded, not {s.tier!r} (crux computes the '
            f'allocations and checks the clock against them)')
    if not b.brief.strip():
        err(f'{s.id}: no brief')
    if not b.debrief.strip():
        warn(f'{s.id}: no debrief; the post-mortem is where this track '
             'teaches, and the score alone teaches nothing')

    allocs = pacing.allocations([sl.track for sl in b.slots], b.budget)
    if abs(sum(allocs) - b.budget) > 1e-6:
        err(f'{s.id}: allocations sum to {sum(allocs):.1f}s, not the '
            f'{b.budget:.1f}s budget')
    for i, (slot, a) in enumerate(zip(b.slots, allocs), 1):
        if a < MIN_ALLOCATION:
            err(f'{s.id}: leg {i} ({slot.track}) is allocated {a:.0f}s, under '
                f'the {MIN_ALLOCATION:.0f}s floor')

    # `target` is capped at 100 by SittingBody, so `need` can never exceed
    # `n` and there is no unreachable-target case to check for. Equality is
    # the whole failure: at that point the pass mark and a clean sweep are
    # the same thing.
    n = len(b.slots)
    need = math.ceil(b.target * n / 100.0)
    if need == n:
        err(f'{s.id}: passing needs all {n} leg{"" if n == 1 else "s"} at '
            f'full marks, so walking away from one is always wrong and the '
            f'sitting cannot teach triage. Lower the target or add a leg')


def check_sitting_fills(reg) -> None:
    """Every slot must resolve to a scenario, on a fresh install and on a
    machine that has played everything.

    Two states rather than one, because they exercise different halves of the
    selection rule: an empty history runs the unseen-first path and a full one
    runs the least-recently-played fallback. A pool that can only be filled
    from one of them is a sitting that breaks for whoever is in the other, and
    that is exactly the sort of thing nobody would reproduce.
    """
    import itertools

    played = State()
    for i, sc in enumerate(reg.scenarios):
        played.record(_stub_attempt(sc, when=1000.0 + i))

    for s in reg.scenarios:
        if not isinstance(s.body, SittingBody):
            continue
        for label, st in (('a fresh install', State()),
                          ('a full history', played)):
            picks = pacing.fill(s.body.slots, reg, st)
            for slot, pick in zip(s.body.slots, picks):
                if pick is None:
                    err(f'{s.id}: a {slot.track} slot cannot be filled on '
                        f'{label}')
                elif pick.track != slot.track:
                    err(f'{s.id}: a {slot.track} slot drew {pick.id}')
            ids = [p.id for p in picks if p is not None]
            if len(ids) != len(set(ids)):
                err(f'{s.id}: the same scenario fills two slots on {label}')
        for slot in s.body.slots:
            known = {sc.id for sc in reg.track(slot.track).scenarios}
            for pid in slot.pool:
                if pid not in known:
                    err(f'{s.id}: pool names {pid!r}, which is not in '
                        f'{slot.track}')


def _stub_attempt(scenario, when: float):
    from crux.state import Attempt
    return Attempt(scenario=scenario.id, track=scenario.track, when=when,
                   elapsed=60.0, total=100.0, marks=100.0, recall=1.0,
                   precision=1.0, tier=scenario.tier)


def check_provenance(reg) -> None:
    """Every cited source must be a real file (crux D11).

    This is the check that pays for itself. Three of the first eleven
    scenarios cited writeups that did not exist, because the paths were
    written from memory of the corpus rather than read out of it, and one of
    them was wrong in a way that mattered: the box it should have cited
    records that the directory returned **403**, not the 200 the scenario had
    been authored around. A citation nobody checks is a citation that drifts.

    Skips silently where the vault is not reachable, because content must run
    on a machine that has never seen it.
    """
    root = vault_dir()
    if root is None:
        print('  note  vault not reachable, provenance not audited '
              '(set $CRUX_VAULT or write .crux-vault)')
        return
    for s in reg.scenarios:
        if not s.source:
            continue
        if not (root / s.source).exists():
            err(f'{s.id}: source does not exist: {s.source}')


def check_scaffolding(reg) -> None:
    """Phase 0 placeholders must not outlive the phase that replaces them."""
    for name in TRACKS:
        scenarios = reg.track(name).scenarios
        smoke = [s for s in scenarios if 'smoke' in s.id]
        real = [s for s in scenarios if 'smoke' not in s.id]
        if smoke and real:
            for s in smoke:
                warn(f'{s.id}: Phase 0 scaffolding still present alongside '
                     f'{len(real)} real scenario(s); delete it')


def check_lineage_ascii(s: Scenario) -> None:
    """Every displayable string in a collection, at the ASCII rung.

    Names are drawn from pools rather than authored, so this is checking the
    pools as much as the content; a single accented surname in `_LAST` would
    reach every scenario in the track at some seed and nowhere else.
    """
    b: LineageBody = s.body
    built = b.canonical()
    for n in built.nodes:
        if not (n.name + n.note).isascii():
            err(f'{s.id}: principal {n.id!r} carries non-ASCII')
    for e in built.edges:
        if not e.why.isascii():
            err(f'{s.id}: right {e.id} carries non-ASCII in its why')
    if not (b.brief + b.debrief + b.objective_note).isascii():
        err(f'{s.id}: the brief or debrief carries non-ASCII')


def check_content_ascii(reg) -> None:
    """No fixture line may carry a non-ASCII character.

    The glyph ladder has an ASCII rung for terminals that cannot render
    anything else, and a screen is only as portable as the text on it. Real
    enumeration tools do draw box characters, and the answer is to author the
    ASCII form they degrade to rather than to lower the rung: the substance
    being drilled is never the border.
    """
    for s in reg.scenarios:
        if isinstance(s.body, LineageBody):
            check_lineage_ascii(s)
        if not isinstance(s.body, MarkBody):
            continue
        for ln in s.body.canonical():
            if not ln.text.isascii():
                bad = [c for c in ln.text if not c.isascii()]
                err(f'{s.id}: line {ln.id!r} carries non-ASCII {bad!r}, which '
                    'would leak into the ASCII glyph rung')
        for a in s.body.actions:
            if not (a.text + a.why).isascii():
                err(f'{s.id}: an action carries non-ASCII')
        if not s.body.debrief.isascii():
            err(f'{s.id}: the debrief carries non-ASCII')


def check_ascii_rung() -> None:
    """Nothing that reaches the ASCII rung may carry a non-ASCII literal."""
    from crux.config import TAGLINE_PARTS, TRACK_BLURB, TIER_MEANING
    pools = {'TAGLINE_PARTS': TAGLINE_PARTS,
             'TRACK_BLURB': tuple(TRACK_BLURB.values()),
             'TIER_MEANING': tuple(TIER_MEANING.values())}
    for label, pool in pools.items():
        for item in pool:
            if not item.isascii():
                err(f'{label}: {item!r} is not ASCII and would leak into the '
                    'ASCII glyph rung')
    joined = len(' . '.join(TAGLINE_PARTS))
    if joined > 38:
        err(f'TAGLINE_PARTS joins to {joined} columns, over the 38 budget')


def check_exit_chord(reg) -> None:
    for s in reg.scenarios:
        if isinstance(s.body, MarkBody):
            for a in s.body.actions:
                if EXIT_CHORD in a.text:
                    err(f'{s.id}: an action claims the reserved exit chord '
                        f'{EXIT_CHORD}')


def check_screen_contract() -> None:
    """Every concrete screen must declare hints and never render blank."""
    import inspect
    import crux.screens as pkg
    from crux.screens import (help as help_mod, home, lineage, mark, proctor,
                              result, stub, track)
    found = 0
    for mod in (help_mod, home, lineage, mark, proctor, result, stub, track):
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if not issubclass(obj, Screen) or obj.__module__ != mod.__name__:
                continue
            found += 1
            if obj.hints is Screen.hints:
                err(f'{obj.__name__}: does not declare key hints')
            if obj.body is Screen.body and not hasattr(obj, 'rows'):
                err(f'{obj.__name__}: renders no body')
    if found < 6:
        err(f'only {found} screens found; the contract check is not reaching them')


#: Marking everything must lose, and it must lose everywhere. A screen small
#: enough that greedy marking still scores respectably cannot teach restraint,
#: and the fix is always more realistic output rather than a harsher scorer.
GREEDY_CEILING = 35.0

_NS_OK = (False, 'not probed')


def score_profile(reg, verbose: bool) -> None:
    """What canonical play patterns score, per scenario.

    This exists because crux D8 is a claim about numbers, and a claim about
    numbers that nobody recomputes becomes false the moment content is added.
    It is also how `DECOY_WEIGHT` stopped being a guess.

    It found a content bug on its first run: the `netstat` fixtures were nine
    lines long, so marking every line scored 31 rather than the 5 it scores on
    a realistic screen. The scorer was fine; the output was too short to be
    wrong on.
    """
    if verbose:
        print(f'\n  score profile (DECOY_WEIGHT={DECOY_WEIGHT})')
        print(f'  {"scenario":<26}{"lines":>6}{"L":>3}{"D":>3}'
              f'{"perfect":>9}{"miss1":>7}{"decoy1":>8}{"greedy":>8}')
    for sc in reg.scenarios:
        if not isinstance(sc.body, MarkBody):
            continue
        lines = sc.body.build(0)
        leads, decoys = roles(lines)
        allids = {ln.id for ln in lines}
        mark = lambda m: score_marks(leads, decoys, m).marks

        greedy = mark(allids)
        if leads:
            perfect = mark(leads)
            miss1 = mark(set(sorted(leads)[1:]))
            decoy1 = mark(leads | set(sorted(decoys)[:1])) if decoys else None
        else:
            perfect = mark(set())
            miss1 = None
            decoy1 = mark(set(sorted(decoys)[:1])) if decoys else None

        if perfect < 100.0:
            err(f'{sc.id}: a perfect answer scores {perfect}, not 100')
        if greedy > GREEDY_CEILING:
            warn(f'{sc.id}: marking every line scores {greedy:.0f}, over the '
                 f'{GREEDY_CEILING:.0f} ceiling. The screen is too short to be '
                 'wrong on; add realistic output rather than harshening the '
                 'scorer')
        if verbose:
            f = lambda v: f'{v:.0f}' if v is not None else '-'
            print(f'  {sc.id:<26}{len(lines):>6}{len(leads):>3}{len(decoys):>3}'
                  f'{perfect:>9.0f}{f(miss1):>7}{f(decoy1):>8}{greedy:>8.0f}')


def path_profile(reg, verbose: bool) -> None:
    """What each lineage graph costs, and what not reading it costs.

    The lineage answer to `--scores`. `greedy` is the score you get by always
    taking the cheapest visible move without reading the collection, measured
    across seeds because the tie-break moves with the names. A graph where
    greedy wins is a graph with no reading in it.
    """
    if not verbose:
        return
    rows = [s for s in reg.scenarios if isinstance(s.body, LineageBody)]
    if not rows:
        return
    print(f'\n  path profile (budget = {LN.BUDGET_FACTOR:g}x the cheapest '
          f'route, floor +{LN.BUDGET_FLOOR})')
    print(f'  {"scenario":<22}{"nodes":>6}{"rights":>7}{"cheap":>7}{"hops":>6}'
          f'{"shortest":>10}{"budget":>8}{"greedy":>8}{"map":>6}   teaches')
    for s in rows:
        built = s.body.canonical()
        best = LN.cheapest(built)
        hops = LN.shortest(built)
        budget = LN.budget_for(best.cost)
        scores = []
        for seed in PROBE_SEEDS:
            bt = s.body.build(seed)
            bc = LN.cheapest(bt).cost
            arrived, spent = _greedy(bt, LN.budget_for(bc))
            scores.append(round(min(100.0, 100.0 * bc / spent), 1)
                          if (arrived and spent) else 0.0)
        mean = sum(scores) / len(scores)
        # What following the fewest-edges route scores: the strategy a
        # collection tool's "shortest path" hands you, and the one a
        # teaches="cost" graph exists to punish.
        by_map = (round(min(100.0, 100.0 * best.cost / hops.cost))
                  if hops.reachable and hops.cost else 0)
        print(f'  {s.id:<22}{len(built.nodes):>6}{len(built.edges):>7}'
              f'{best.cost:>7}{best.hops:>6}'
              f'{f"{hops.hops}h/{hops.cost}c":>10}{budget:>8}{mean:>8.0f}'
              f'{by_map:>6}   {s.body.teaches or "-"}')
        culs = _culdesacs(built)
        if culs:
            print('       cul-de-sacs: '
                  + ', '.join(f'{built.label(e.dst)} ({LN.cost_of(e.kind)})'
                              for e in culs))


def pacing_profile(reg, verbose: bool) -> None:
    """Every sitting's allocations, beside what real play actually costs.

    This is the tuning path for `pacing.TRACK_WEIGHT`, and it is deliberately
    weaker than `--scores` is for `DECOY_WEIGHT`. The decoy weight could be
    settled from the content alone, because what a greedy answer scores is a
    property of the authored screens. How long a leg takes is a property of a
    person, so the only evidence that can settle the track weights is recorded
    play, and until there is enough of it this prints the sample size and
    declines to draw a conclusion. Guessing quietly is the failure mode; the
    number being provisional is not.
    """
    if not verbose:
        return
    st = State.load()
    hist = pacing.history(st.attempts)
    print(f'\n  pacing profile (TRACK_WEIGHT={pacing.TRACK_WEIGHT})')
    print(f'  {"track":<10}{"weight":>8}{"runs":>7}{"median":>10}'
          f'{"longest":>10}   verdict')
    for t in hist.tracks:
        w = pacing.weight(t.track)
        if not t.completed:
            verdict = ('no play recorded' if not t.attempts
                       else 'every attempt was walked away from')
            med = longest = '-'
        elif t.thin:
            verdict = f'sample under {pacing.SAMPLE_FLOOR}, not read'
            med, longest = fmt_s(t.median), fmt_s(t.longest)
        else:
            verdict = 'readable'
            med, longest = fmt_s(t.median), fmt_s(t.longest)
        print(f'  {t.track:<10}{w:>8.1f}{t.completed:>7}{med:>10}'
              f'{longest:>10}   {verdict}')

    readable = [t for t in hist.tracks if t.completed and not t.thin]
    if len(readable) > 1:
        base = min(t.median for t in readable)
        print('  measured ratio (base = fastest readable track):')
        for t in readable:
            print(f'    {t.track:<10}{t.median / base:>6.1f}  '
                  f'against a weight of {pacing.weight(t.track):.1f}')
    else:
        print(f'  not enough readable tracks to check the weights; '
              f'{pacing.SAMPLE_FLOOR} attempts per track is the floor')

    import math
    for s in reg.scenarios:
        if not isinstance(s.body, SittingBody):
            continue
        b: SittingBody = s.body
        allocs = pacing.allocations([sl.track for sl in b.slots], b.budget)
        n = len(b.slots)
        need = math.ceil(b.target * n / 100.0)
        print(f'\n  {s.id}   {fmt_s(b.budget)} budget, pass on '
              f'{b.target:.0f}, {need} of {n} legs at full marks')
        picks = pacing.fill(b.slots, reg, State())
        for slot, a, pick in zip(b.slots, allocs, picks):
            name = pick.id if pick is not None else 'UNFILLABLE'
            print(f'    {slot.track:<9}{fmt_s(a):>8}   {name}')


def fmt_s(seconds: float) -> str:
    from crux.clock import fmt
    return fmt(seconds)


def main() -> int:
    global _NS_OK
    from crux.targets.netns import capability
    _NS_OK = capability()
    reg = load()
    check_registry(reg)
    for s in reg.scenarios:
        check_scenario(s)
    check_provenance(reg)
    check_scaffolding(reg)
    check_sitting_fills(reg)
    score_profile(reg, verbose='--scores' in sys.argv)
    pacing_profile(reg, verbose='--pacing' in sys.argv)
    path_profile(reg, verbose='--paths' in sys.argv)
    if '--fast' not in sys.argv:
        check_salvage_runs(reg)
        check_conduit_runs(reg)
        check_chain_runs(reg)
    check_ascii_rung()
    check_content_ascii(reg)
    check_exit_chord(reg)
    check_screen_contract()

    print(f'crux {VERSION}')
    marks = [s for s in reg.scenarios if isinstance(s.body, MarkBody)]
    builds = [s.body.canonical() for s in marks]
    total_lines = sum(len(b) for b in builds)
    total_leads = sum(len(roles(b)[0]) for b in builds)
    total_decoys = sum(len(roles(b)[1]) for b in builds)
    total_actions = sum(len(s.body.actions) for s in marks)
    no_lead = sum(1 for b in builds if not roles(b)[0])
    for name in TRACKS:
        tr = reg.track(name)
        state = 'ready' if tr.ready else 'engine not built yet'
        print(f'  {name:<9}{len(tr.scenarios):>3} scenario(s)   {state}')
    print(f'  fixtures  {len(marks)} built, {total_lines} lines, '
          f'{total_leads} lead(s), {total_decoys} decoy(s), '
          f'{total_actions} action(s), {no_lead} with no lead')
    print(f'  seeds     each fixture built at {len(PROBE_SEEDS)} seeds, '
          'key stable across all')
    cond = [s for s in reg.scenarios if isinstance(s.body, ConduitBody)]
    if cond:
        hops = sum(len(s.body.topology.links) for s in cond)
        probes = sum(len(s.body.topology.probes) for s in cond)
        usable, why = _NS_OK
        gated = sum(1 for s in cond if missing_needs(s))
        line = (f'  conduit   {len(cond)} topologies, {hops} link(s), '
                f'{probes} probe(s); namespaces '
                + ('usable here' if usable else f'UNAVAILABLE ({why})'))
        if gated:
            line += f'; {gated} gated on a missing tool'
        print(line)
    lin = [s for s in reg.scenarios if isinstance(s.body, LineageBody)]
    if lin:
        graphs = [s.body.canonical() for s in lin]
        nodes = sum(len(g.nodes) for g in graphs)
        rights = sum(len(g.edges) for g in graphs)
        culs = sum(len(_culdesacs(g)) for g in graphs)
        print(f'  lineage   {len(lin)} collection(s), {nodes} principals, '
              f'{rights} rights, {culs} branch(es) that go nowhere')
        print('  routes    every objective reachable, cheapest route stable '
              'across all seeds')
    sits = [s for s in reg.scenarios if isinstance(s.body, SittingBody)]
    if sits:
        legs = sum(len(s.body.slots) for s in sits)
        budget = sum(s.body.budget for s in sits)
        print(f'  proctor   {len(sits)} sitting(s), {legs} leg(s), '
              f'{budget / 60:.0f} minutes of budget')
        print('  slots     every slot fills on a fresh install and on a '
              'full history')
    chains = [s for s in reg.scenarios if isinstance(s.body, ChainBody)]
    if chains:
        print(f'  chain     {len(chains)} engagement(s), '
              f'{sum(len(c.body.stages) for c in chains)} stages, each a '
              'real run of its track')
    salv = [s for s in reg.scenarios if isinstance(s.body, SalvageBody)]
    if salv:
        reqs = sum(len(s.body.requirements) for s in salv)
        defects = sum(len(s.body.defects) for s in salv)
        http = sum(1 for s in salv if s.body.kind == 'http')
        print(f'  salvage   {len(salv)} scripts ({http} http, '
              f'{len(salv) - http} tcp), {reqs} requirement(s), '
              f'{defects} defect(s)')
        if '--fast' in sys.argv:
            print('  note      --fast: reference solutions were NOT run')
        else:
            traps = sum(1 for s in salv if s.body.trap)
            print('  proven    every solution landed against a real target; '
                  'every broken')
            print(f'            script failed'
                  + (f', and all {traps} trap script(s) tripped their sink'
                     if traps else ''))

    for w in WARNINGS:
        print(f'  WARN  {w}')
    for e in ERRORS:
        print(f'  ERROR {e}')
    print(f'{len(ERRORS)} error(s), {len(WARNINGS)} warning(s)')
    return 1 if ERRORS else 0


if __name__ == '__main__':
    raise SystemExit(main())
