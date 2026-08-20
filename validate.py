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
from crux.model import LINE_KINDS, MarkBody, Scenario, StubBody, roles
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
    elif isinstance(s.body, StubBody):
        if s.tier != 'self':
            err(f'{s.id}: a stub must be self tier, not {s.tier!r} '
                f'(crux D6: never claim a check that is not happening)')
        if not s.body.phase:
            err(f'{s.id}: a stub must name the phase that builds it')
    else:
        err(f'{s.id}: unknown body type {type(s.body).__name__}')


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
    reg = load()
    check_registry(reg)
    for s in reg.scenarios:
        check_scenario(s)
    check_provenance(reg)
    check_scaffolding(reg)
    score_profile(reg, verbose='--scores' in sys.argv)
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

    for w in WARNINGS:
        print(f'  WARN  {w}')
    for e in ERRORS:
        print(f'  ERROR {e}')
    print(f'{len(ERRORS)} error(s), {len(WARNINGS)} warning(s)')
    return 1 if ERRORS else 0


if __name__ == '__main__':
    raise SystemExit(main())
