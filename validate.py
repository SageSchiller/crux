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
from crux.config import EXIT_CHORD, TIERS, TRACKS, vault_dir
from crux.loader import load
from crux.model import (LINE_KINDS, ConduitBody, MarkBody, SalvageBody,
                        Scenario, StubBody, roles)
from crux.scoring import DECOY_WEIGHT, score_marks
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
    for name in TRACKS:
        if name not in reg.tracks:
            err(f'track {name} did not load at all')


def check_scenario(s: Scenario) -> None:
    if s.track not in TRACKS:
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


def check_content_ascii(reg) -> None:
    """No fixture line may carry a non-ASCII character.

    The glyph ladder has an ASCII rung for terminals that cannot render
    anything else, and a screen is only as portable as the text on it. Real
    enumeration tools do draw box characters, and the answer is to author the
    ASCII form they degrade to rather than to lower the rung: the substance
    being drilled is never the border.
    """
    for s in reg.scenarios:
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
    from crux.screens import help as help_mod, home, mark, result, stub, track
    found = 0
    for mod in (help_mod, home, mark, result, stub, track):
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
    score_profile(reg, verbose='--scores' in sys.argv)
    if '--fast' not in sys.argv:
        check_salvage_runs(reg)
        check_conduit_runs(reg)
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
        print(f'  conduit   {len(cond)} topologies, {hops} link(s), '
              f'{probes} probe(s); namespaces '
              + ('usable here' if usable else f'UNAVAILABLE ({why})'))
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
