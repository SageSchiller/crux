#!/usr/bin/env python3
"""Behavioural checks. Green means every assertion below passed.

Runs with no TTY, which is why everything that touches `termios` is quarantined
in `term.py` and nothing here imports it for anything but the pure helpers.

The check that matters most is `test_walkthrough`: it drives the real screen
stack with real keypresses from the track picker to a recorded result. Unit
tests on a scorer prove arithmetic; that one proves the app.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# State must not touch the real history. Set before crux.config is imported.
_TMP = Path(tempfile.mkdtemp(prefix='crux-test-'))
os.environ['XDG_DATA_HOME'] = str(_TMP)

from crux import keys as K                                    # noqa: E402
from crux import render as R                                  # noqa: E402
from crux.clock import FakeClock, Stopwatch, fmt              # noqa: E402
from crux.config import CHAIN, MIN_COLS, MIN_ROWS, SECTIONS, TRACKS  # noqa: E402
from crux.loader import load                                  # noqa: E402
from crux.model import (ChainBody, ConduitBody, ContentError,  # noqa: E402
                        Line, MarkBody, SalvageBody, Scenario,
                        Stage, roles)
from crux import lineage as LN                                # noqa: E402
from crux.scoring import DECOY_WEIGHT, band, score_marks      # noqa: E402
from crux.screens import Screen                               # noqa: E402
from crux.screens.help import HelpScreen                      # noqa: E402
from crux.screens.home import HomeScreen                      # noqa: E402
from crux.session import Session                              # noqa: E402
from crux.state import Attempt, State                         # noqa: E402
from crux.theme import PALETTES                               # noqa: E402

CHECKS = 0
FAILURES: list[str] = []


def ok(cond: bool, what: str) -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(what)


def eq(got, want, what: str) -> None:
    ok(got == want, f'{what}: got {got!r}, want {want!r}')


# --------------------------------------------------------------------------
# Capability matrix, used by every rendering check
# --------------------------------------------------------------------------

def all_caps(cols: int = MIN_COLS, rows: int = MIN_ROWS):
    out = []
    for pal in PALETTES.values():
        for color in R.ColorLevel:
            if pal.name == 'ansi' and color > R.ColorLevel.C16:
                continue
            for glyphs in R.GlyphLevel:
                out.append(R.Caps(color=color, glyphs=glyphs, palette=pal,
                                  cols=cols, rows=rows))
    return out


# --------------------------------------------------------------------------

def test_keys() -> None:
    for s in ('C-b', 'SPC', 'M-x', 'RET', 'F10', 'a', '"', 'C-M-S-F5', 'Up'):
        k = K.parse(s)
        eq(K.unparse(k), s if s != '"' else '"', f'key roundtrip {s}')
    ok(K.parse("S-'") == K.parse('"'), 'shifted quote normalises')
    ok(K.parse('TAB') != K.parse('C-i'), 'TAB and C-i are distinct objects')
    ok('C-i' in K.AMBIGUOUS_LEGACY.values(), 'legacy ambiguity is recorded')
    d = K.Decoder()
    out = d.feed(b'ab')
    eq([k.name for k in out], ['a', 'b'], 'decoder plain bytes')

    # The decoder and the notation must produce the same Key for the same key,
    # or every screen that compares against parse('X') silently never matches.
    # Space was wrong for the whole of Phase 0 and no unit test could see it,
    # because a test that builds input with parse() only asks the notation
    # whether it agrees with itself. This asks the bytes.
    for raw, notation in ((b' ', 'SPC'), (b'\r', 'RET'), (b'\t', 'TAB'),
                          (b'\x1b', 'ESC'), (b'\x7f', 'BSP'), (b'a', 'a'),
                          (b'\x01', 'C-a'), (b'\x1b[A', 'Up'),
                          (b'\x1b[B', 'Down'), (b'\x1b[21~', 'F10')):
        for kitty in (False, True):
            dec = K.Decoder(kitty=kitty)
            got = dec.feed(raw) or dec.flush()
            ok(bool(got) and got[0] == K.parse(notation),
               f'decoder agrees with notation for {notation} '
               f'(kitty={kitty}): got {got[0] if got else None}')


def test_render_primitives() -> None:
    caps = all_caps()[0]
    t = R.Text().add('hello').add(' world')
    eq(t.width(), 11, 'Text width')
    eq(t.plain(), 'hello world', 'Text plain')
    t.truncate(8, '...')
    ok(t.width() <= 8, 'truncate respects the budget')
    t2 = R.Text().add('x').pad_to(5)
    eq(t2.width(), 5, 'pad_to')
    eq(R.text_width('a'), 1, 'ascii width')
    eq(R.text_width('中'), 2, 'cjk width is 2')
    eq(R.strip_markup('a `b` **c**'), 'a b c', 'markup stripped for width')
    rows = R.wrap('one two three four five', 10)
    ok(all(len(r) <= 10 for r in rows), 'wrap respects width')
    ok(R.footer(caps, [('q', 'quit')]).width() > 0, 'footer renders')
    try:
        R.footer(caps, [])
        ok(False, 'empty footer must raise')
    except ValueError:
        ok(True, 'empty footer raises')


def test_scoring() -> None:
    leads = {'a', 'b'}
    decoys = {'d1', 'd2', 'd3'}
    noise = {f'n{i}' for i in range(35)}
    every = leads | decoys | noise

    perfect = score_marks(leads, decoys, leads)
    eq(perfect.total, 100.0, 'perfect marking scores 100')
    ok(perfect.clean_pass, 'perfect marking is a clean pass')

    greedy = score_marks(leads, decoys, every)
    ok(greedy.recall == 1.0, 'marking everything has perfect recall')
    ok(greedy.total < 15, 'crux D8: marking everything must lose')
    ok(greedy.total < perfect.total, 'greedy scores below precise')

    half = score_marks(leads, decoys, {'a'})
    one_decoy = score_marks(leads, decoys, leads | {'d1'})
    eq(round(half.total, 1), round(one_decoy.total, 1),
       'crux D8: missing a lead costs what chasing a decoy costs')

    stray = score_marks(leads, decoys, leads | {'n1'})
    ok(one_decoy.total < stray.total,
       f'a decoy costs more than a stray mark (weight {DECOY_WEIGHT})')

    nothing = score_marks(leads, decoys, set())
    eq(nothing.total, 0.0, 'marking nothing when there are leads scores 0')

    # crux D9: the no-lead case
    quiet = score_marks(set(), decoys, set())
    eq(quiet.total, 100.0, 'crux D9: correctly saying nothing is here scores 100')
    ok(quiet.no_lead and quiet.clean_pass, 'no-lead clean pass')
    ok('and you said so' in quiet.summary(), 'no-lead summary reads right')
    chased = score_marks(set(), decoys, {'d1'})
    ok(chased.total < 50, 'crux D9: chasing a phantom is punished')

    # the act beat is worth exactly ACTION_POINTS
    with_act = score_marks(leads, decoys, leads, action_ok=True, has_action=True)
    without = score_marks(leads, decoys, leads, action_ok=False, has_action=True)
    eq(with_act.total, 100.0, 'perfect marks plus right action is 100')
    eq(round(with_act.total - without.total, 1), 25.0, 'act beat is worth 25')
    ok(not without.clean_pass, 'a wrong action is not a clean pass')

    eq(band(95), 'clean', 'band clean')
    eq(band(10), 'lost', 'band lost')
    ok('chased 1' in one_decoy.summary(), 'summary names what was chased')


def test_clock() -> None:
    c = FakeClock()
    w = Stopwatch(c)
    w.start()
    c.advance(30)
    eq(w.elapsed(), 30.0, 'stopwatch accrues')
    w.pause()
    c.advance(600)
    eq(w.elapsed(), 30.0, 'a paused watch does not accrue over lunch')
    w.start()
    c.advance(12)
    eq(w.elapsed(), 42.0, 'resume continues')
    eq(fmt(42), '42s', 'fmt seconds')
    eq(fmt(90), '1m 30s', 'fmt minutes')
    eq(fmt(3661), '1h 01m', 'fmt hours')
    w2 = Stopwatch(FakeClock())
    eq(w2.elapsed(), 0.0, 'an unstarted watch reads zero')


def test_state() -> None:
    p = _TMP / 'roundtrip.json'
    s = State()
    s.record(Attempt('x', 'sift', 10.0, 5.0, 90.0, 90.0, 1.0, 1.0, 'graded',
                     1, ('a',), True))
    s.save(p)
    back = State.load(p)
    eq(back.attempts, s.attempts, 'state roundtrips')
    eq(back.best('x').total, 90.0, 'best score found')
    eq(back.track_summary('sift'), (1, 90.0), 'track summary')
    eq(back.time_on_task(), 5.0, 'time on task is preserved')

    merged = State()
    eq(merged.merge(back), 1, 'merge adds new rows')
    eq(merged.merge(back), 0, 'merge is idempotent')

    bad = _TMP / 'bad.json'
    bad.write_text('{not json', encoding='utf-8')
    damaged = State.load(bad)
    ok(damaged.damaged and not damaged.attempts,
       'a corrupt state file is reported, not thrown')
    eq(State.load(_TMP / 'missing.json').attempts, [],
       'a missing state file is an empty history')


def test_model_guards() -> None:
    for bad in (
        lambda: Line('x', 'y', 'nonsense'),
        lambda: Scenario(id='a', track='nope', title='t', tier='graded'),
        lambda: Scenario(id='a', track='sift', title='t', tier='nope'),
        lambda: Scenario(id='has space', track='sift', title='t', tier='graded'),
    ):
        try:
            bad()
            ok(False, 'malformed content must raise ContentError')
        except ContentError:
            ok(True, 'malformed content raises')


def test_loader() -> None:
    reg = load()
    eq(reg.errors, [], 'content loads with no errors')
    eq(sorted(reg.tracks), sorted(SECTIONS),
       'all sections present, the three tracks plus chain')
    ok(len(reg.scenarios) >= 3, 'at least one scenario per track')
    ok(reg.by_id('sift-nmap-pinned') is not None, 'lookup by id')
    ok(reg.by_id('nope') is None, 'unknown id returns None')
    ok(reg.track('sift').ready, 'sift has a real engine')
    ok(reg.track('salvage').ready, 'salvage has a real engine now')
    ok(reg.track('conduit').ready, 'conduit has a real engine now')
    chains = reg.track('chain').scenarios
    ok(len(chains) >= 2, f'{len(chains)} chain engagements')
    # The two engagements must not be the same box twice: the exam is half
    # Linux and half domain, so the capstone has to cover both shapes.
    from crux.config import TRACKS as _TRACKS
    from crux.model import ChainBody as _CB
    kinds = set()
    for c in chains:
        if isinstance(c.body, _CB):
            kinds.add(tuple(st.track for st in c.body.stages))
            # A chain is a prefix of the engagement order, three or four legs.
            tracks = tuple(st.track for st in c.body.stages)
            ok(3 <= len(tracks) <= 4,
               f'{c.id}: an engagement is three or four stages')
            ok(all(t in _TRACKS for t in tracks),
               f'{c.id}: every stage is a skill track')
    ids = {c.id for c in chains}
    ok('chain-wexler' in ids and 'chain-northwind' in ids,
       'both the single-host and the domain engagements are present')
    ok('chain-aldwych' in ids,
       'and the four-stage engagement that ends on a graph walk')
    ok(len(reg.track('sift').scenarios) >= 9, 'sift has real breadth')
    ok(reg.by_id('sift-smoke-nmap') is None,
       'Phase 0 scaffolding was deleted, not left beside real content')
    from crux.model import StubBody as _SB
    ok(not any(isinstance(sc.body, _SB) for sc in reg.scenarios),
       'no track is still standing on a placeholder')


def test_fixtures() -> None:
    """The crux D10 properties, asserted rather than assumed."""
    reg = load()
    sifts = [s for s in reg.track('sift').scenarios
             if isinstance(s.body, MarkBody)]
    ok(bool(sifts), 'there are sift scenarios to check')

    moved = 0
    for sc in sifts:
        b: MarkBody = sc.body
        a1, a2 = b.build(4242), b.build(4242)
        eq([l.text for l in a1], [l.text for l in a2],
           f'{sc.id}: the same seed builds the same screen')
        ok([l.text for l in b.build(1)] != [l.text for l in b.build(2)],
           f'{sc.id}: different seeds build different screens')

        keys = {frozenset(roles(b.build(sd))[0]) for sd in (0, 3, 77, 4242)}
        eq(len(keys), 1, f'{sc.id}: the key does not move with the seed')

        for sd in (0, 3, 77, 4242):
            ids = [l.id for l in b.build(sd)]
            eq(len(ids), len(set(ids)), f'{sc.id}: line ids unique at seed {sd}')

        # The anti-memorisation property: for a fixture with generated noise,
        # the lead must not sit at the same index every time, or the scenario
        # is beatable by remembering a row number.
        leads = roles(b.build(0))[0]
        if leads:
            positions = set()
            for sd in range(24):
                lines = b.build(sd)
                positions.add(tuple(i for i, l in enumerate(lines)
                                    if l.id in leads))
            if len(positions) > 1:
                moved += 1
    ok(moved >= 12,
       f'only {moved} fixtures move their lead between seeds; crux D10 wants '
       'a screen that cannot be beaten by remembering a row number')

    no_lead = [sc for sc in sifts if sc.body.no_lead]
    ok(len(no_lead) >= 4,
       f'{len(no_lead)} no-lead scenarios; crux D9 needs the possibility live')
    ok(len(no_lead) < len(sifts) / 2,
       'no-lead scenarios must stay the exception, or the app trains the '
       'opposite reflex: mark nothing and always be half right')


def test_scoring_over_real_content() -> None:
    """crux D8 is a claim about numbers, so recompute it over every screen."""
    from crux.scoring import DECOY_WEIGHT
    reg = load()
    for sc in reg.track('sift').scenarios:
        if not isinstance(sc.body, MarkBody):
            continue
        lines = sc.body.build(0)
        leads, decoys = roles(lines)
        allids = {ln.id for ln in lines}
        mark = lambda m: score_marks(leads, decoys, m).marks

        eq(mark(leads if leads else set()), 100.0,
           f'{sc.id}: the correct answer scores 100')
        greedy = mark(allids)
        ok(greedy <= 35.0,
           f'{sc.id}: marking every line scores {greedy:.0f}, which is not '
           'losing badly enough for crux D8')
        ok(bool(decoys), f'{sc.id}: has at least one line authored to tempt')
        if len(leads) > 1 and decoys:
            miss1 = mark(set(sorted(leads)[1:]))
            decoy1 = mark(leads | set(sorted(decoys)[:1]))
            eq(round(miss1, 1), round(decoy1, 1),
               f'{sc.id}: missing a lead costs what chasing a decoy costs')


def _screens(session):
    """One instance of every screen, reachable the way a user reaches them."""
    from crux.screens.mark import ActScreen, MarkScreen
    from crux.screens.result import ResultScreen
    from crux.screens.stub import StubScreen
    from crux.screens.track import TrackScreen
    from crux.screens.home import ErrorScreen
    from crux.screens.lineage import MapScreen, WalkResultScreen, WalkScreen
    from crux.screens.proctor import PacingScreen, SittingIntroScreen

    sift = session.registry.by_id('sift-nmap-pinned')
    wide = session.registry.by_id('sift-nmap-dc')
    # No content uses StubBody any more: all three tracks have real engines.
    # The screen stays, because tracks four and five will land the same way,
    # so it is tested against a scenario built here rather than dropped.
    from crux.model import StubBody
    stub = Scenario(id='stub-probe', track='conduit', tier='self',
                    title='Engine not built yet',
                    body=StubBody(prompt='a future track lands here',
                                  phase='Phase 8', debrief='not yet'))
    mark = MarkScreen(session, sift, seed=0)
    walk = WalkScreen(session, session.registry.by_id('lineage-reset'), seed=0)
    lead = sorted(mark.leads)[0]
    watch = Stopwatch(session.clock)
    score = score_marks(mark.leads, mark.decoys, {lead},
                        action_ok=True, has_action=True, elapsed=61.0)
    return [
        HomeScreen(session),
        TrackScreen(session, 'sift'),
        TrackScreen(session, 'conduit'),
        mark,
        MarkScreen(session, wide, seed=0),
        ActScreen(session, sift, (lead,), watch, mark.lines, 0),
        ResultScreen(session, sift, score, mark.lines,
                     chose=sift.body.actions[0]),
        StubScreen(session, stub),
        HelpScreen(),
        HelpScreen('lineage'),
        ErrorScreen(session),
        TrackScreen(session, 'lineage'),
        TrackScreen(session, 'proctor'),
        walk,
        MapScreen(walk),
        WalkResultScreen(walk, LN.score_walk(
            walk.built, list(walk.best.priced), True, walk.best.cost,
            walk.budget, elapsed=94.0)),
        SittingIntroScreen(session, session.registry.by_id('proctor-short')),
        PacingScreen(session),
    ]


def test_screens_render() -> None:
    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    for size in ((MIN_COLS, MIN_ROWS), (40, 16), (200, 60)):
        for caps in all_caps(*size):
            for scr in _screens(session):
                name = f'{type(scr).__name__}@{size[0]}x{size[1]}/{caps.color.name}'
                rows = scr.render(caps)
                ok(bool(rows), f'{name}: renders something')
                ok(len(rows) <= caps.rows,
                   f'{name}: {len(rows)} rows exceeds {caps.rows}')
                for r in rows:
                    ok(r.width() <= caps.cols,
                       f'{name}: line of {r.width()} exceeds {caps.cols}')
                if caps.glyphs is R.GlyphLevel.ASCII:
                    plain = ''.join(r.plain() for r in rows)
                    ok(plain.isascii(),
                       f'{name}: non-ASCII leaked into the ASCII rung')
                # Screen contract rule 4, asserted against the *frame* rather
                # than against the hint list. A hint that exists and is then
                # clipped off the edge by the frame has advertised nothing,
                # which is precisely what happened the first time a sitting
                # added its abandon key to an already-full marking footer.
                # Only checked where the frame is at least the documented
                # minimum: below that the height backstop is allowed to eat
                # rows, and it is allowed to eat these.
                # The frame must close. A header whose title and right-hand
                # label together ran past the width used to lose its own
                # corner to the backstop truncation, which reads as a torn
                # box on precisely the screens with the most to say.
                ok(rows[0].plain().endswith(caps.g('tr')),
                   f'{name}: the top border lost its corner')
                ok(rows[-1].plain().endswith(caps.g('br')),
                   f'{name}: the bottom border lost its corner')
                if size[0] >= MIN_COLS and size[1] >= MIN_ROWS:
                    painted = '\n'.join(r.plain() for r in rows)
                    for key, label in scr.hints(caps):
                        ok(f'{key} {label}' in painted,
                           f'{name}: the footer promises {key!r} and the '
                           f'frame clipped it')


def test_every_scenario_renders() -> None:
    """Every sift screen, at the narrowest terminal and the poorest rung.

    `_screens` instantiates two scenarios, which was fine when there were
    eleven and is not fine at twenty-six: content is where non-ASCII and
    overlong lines actually get introduced, and a render test that only sees
    two of them is testing the harness rather than the content.
    """
    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    from crux.screens.mark import MarkScreen
    poor = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                  next(iter(PALETTES.values())), MIN_COLS, MIN_ROWS)
    rich = R.Caps(R.ColorLevel.TRUE, R.GlyphLevel.UNICODE,
                  next(iter(PALETTES.values())), 120, 45)
    for sc in session.registry.track('sift').scenarios:
        for caps in (poor, rich):
            scr = MarkScreen(session, sc, seed=0)
            rows = scr.render(caps)
            ok(bool(rows), f'{sc.id}: renders')
            for r in rows:
                ok(r.width() <= caps.cols,
                   f'{sc.id}: line of {r.width()} exceeds {caps.cols}')
            if caps is poor:
                plain = ''.join(r.plain() for r in rows)
                ok(plain.isascii(),
                   f'{sc.id}: non-ASCII leaked into the ASCII rung')
                ok(any(h[1] == 'submit' for h in scr.hints(caps)),
                   f'{sc.id}: offers a way to submit')


def test_mock_targets() -> None:
    """The two mock services, including the line protocol that got fixed."""
    import socket
    import urllib.error
    import urllib.request

    from crux.targets._hits import HitRecord, Request, Requirement
    from crux.targets.mockhttp import MockHttp
    from crux.targets.mocktcp import MockTcp

    reqs = (Requirement('verb', 'method', 'POST', hint='must be POST'),
            Requirement('path', 'route', '/a/b', hint='wrong endpoint'),
            Requirement('field', 'form', 'zap', key='cmd', hint='no payload'))

    def send(url, data=None, headers=None):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, data=data,
                                       headers=headers or {})).read()
        except urllib.error.HTTPError as e:
            return e.read()

    with MockHttp(reqs, route='/a/b') as t:
        ok(t.port > 0, 'the http target got a port')
        ok(t.url.startswith('http://127.0.0.1:'),
           'the http target binds loopback only (crux D2)')
        eq(t.verdict()[0], False, 'nothing landed before anything was sent')
        eq(t.verdict()[1], 'Nothing reached the target at all.',
           'an untouched target says so')

        send(f'{t.url}/wrong', data=b'cmd=zap')
        eq(t.verdict()[1], 'wrong endpoint', 'names the first unmet condition')
        eq(t.verdict()[2], 2, 'counts what the closest attempt did meet')

        send(f'{t.url}/a/b', data=b'cmd=nope')
        eq(t.verdict()[1], 'no payload', 'moves on to the next unmet one')

        body = send(f'{t.url}/a/b', data=b'cmd=zap').decode()
        ok(t.verdict()[0], 'a fully correct request lands')
        ok('CRUX-LANDED' in body, 'the target says so in its response too')
        eq(t.record.count, 3, 'every request was recorded')
    eq(t.port, 0, 'the port is released on stop')
    t.stop()
    ok(True, 'stop is idempotent')

    # The line protocol. A single-read target scored the two-line handshake on
    # its first line only, which made the reference solution fail.
    tcp = (Requirement('auth', 'raw', 'AUTH tok', hint='no auth line'),
           Requirement('cmd', 'raw', 'GO', hint='no command'))
    with MockTcp(tcp, banner=b'ready\n') as t:
        s1 = socket.create_connection(('127.0.0.1', t.port), timeout=5)
        eq(s1.recv(64), b'ready\n', 'the banner is sent first')
        s1.sendall(b'GO now\n')
        ok(b'ERR' in s1.recv(64), 'a command without auth is refused')
        s1.close()
        eq(t.verdict()[0], False, 'and it did not land')

        s2 = socket.create_connection(('127.0.0.1', t.port), timeout=5)
        s2.recv(64)
        s2.sendall(b'AUTH tok\n')
        ok(b'ERR' in s2.recv(64), 'auth alone is not enough')
        s2.sendall(b'GO now\n')
        ok(b'CRUX-LANDED' in s2.recv(64),
           'two lines in one connection land (the line-protocol fix)')
        s2.close()
        ok(t.verdict()[0], 'the record agrees')

    rec = HitRecord(())
    eq(rec.landed(), False, 'a target with no requirements never lands')


def test_salvage_content() -> None:
    """Every solution lands and every broken script does not.

    `validate.py` runs these as subprocesses against a live target, which is
    the authoritative check. This one is cheaper and structural: it asserts
    the pair exists, differs, and is wired to requirements that can be met.
    """
    reg = load()
    salv = [s for s in reg.track('salvage').scenarios
            if isinstance(s.body, SalvageBody)]
    ok(len(salv) >= 10,
       f'{len(salv)} salvage scenarios; the plan wants all ten defect classes')
    ok(any(sc.body.trap for sc in salv),
       'the crux D19 capstone is present')
    ok(any(sc.body.framing == 'length' for sc in salv),
       'the length-framed target is exercised by real content')
    kinds = {s.body.kind for s in salv}
    ok('tcp' in kinds and 'http' in kinds,
       'both mock targets are exercised by real content, not only by tests')
    for sc in salv:
        b = sc.body
        eq(sc.tier, 'verified', f'{sc.id}: salvage is verified')
        ok(b.broken != b.solution, f'{sc.id}: the pair differs')
        ok(bool(b.requirements), f'{sc.id}: has requirements')
        ok(all(q.hint for q in b.requirements),
           f'{sc.id}: every requirement can explain itself')
        ok(bool(b.defects), f'{sc.id}: names its defect classes')
        ok(b.cve.startswith('CVE-') and b.models,
           f'{sc.id}: is grounded in a real CVE and product')
        ok(bool(b.real_note),
           f'{sc.id}: carries an in-the-wild note tying it to the real PoC')
        rendered = b.render(b.broken, 'http://127.0.0.1:1', 1)
        # Not a bare '{{' check: the template-injection payload legitimately
        # contains one, which is the whole point of that scenario.
        for marker in ('{{URL}}', '{{PORT}}'):
            ok(marker not in rendered,
               f'{sc.id}: {marker} was not substituted')


def test_salvage_screen() -> None:
    """The screen opens a real target, writes the file, and scores a run."""
    from crux.screens.salvage import SalvageScreen
    from crux.screens.runresult import RunResultScreen
    import subprocess

    session = Session.open(clock=FakeClock(), read_only=True)
    sc = session.registry.by_id('salvage-encoding')
    scr = SalvageScreen(session, sc)
    try:
        eq(scr.error, '', 'the target opened')
        ok(scr.path is not None and scr.path.exists(),
           'the broken script was written to disk')
        ok('{{' not in scr.path.read_text(), 'the markers were substituted')
        ok(scr.url.startswith('http://127.0.0.1:'), 'loopback only')

        caps = all_caps()[0]
        ok(bool(scr.render(caps)), 'the salvage screen renders')
        ok(any(h[0] == 'r' for h in scr.hints(caps)), 'it offers run')

        # Running the broken script must not land, and must say why.
        scr._run()
        eq(scr.runs, 1, 'the run was counted')
        eq(scr.read_first, False,
           'running without opening it first is recorded (crux D19)')
        landed, detail, met = scr.target.verdict()
        ok(not landed, 'the broken script does not land')
        ok('survive' in detail, 'and the feedback names the encoding gap')

        # Now the reference fix, through the same screen.
        scr.path.write_text(sc.body.render(sc.body.solution, scr.url, 0))
        action = scr._run()
        eq(action.kind, 'replace', 'landing moves to the result screen')
        res = action.screen
        ok(isinstance(res, RunResultScreen), 'and it is the run result')
        ok(res.score.landed, 'the score says it landed')
        eq(res.score.total_score, 100.0, 'a landed exploit scores 100')
        eq(res.score.runs, 2, 'both runs were counted')
        ok(bool(res.render(caps)), 'the result screen renders')
        eq(len(session.state.attempts), 1, 'exactly one attempt recorded')
        eq(session.state.attempts[0].runs, 2, 'runs reached history')
        eq(session.state.attempts[0].read_first, False,
           'read_first reached history')
    finally:
        scr.close()
        scr.close()
    ok(True, 'closing the salvage screen twice is safe')


def test_length_framing() -> None:
    """A frame whose header lies gets truncated, which is the whole defect."""
    import socket
    import struct

    from crux.targets._hits import Requirement
    from crux.targets.mocktcp import MockTcp

    reqs = (Requirement('whole command', 'raw', 'GO;id;#', hint='truncated'),)
    with MockTcp(reqs, framing='length', banner=b'framed\n') as t:
        body = b'GO;id;#'
        for label, delta, want in (('short by one', -1, False),
                                   ('exact', 0, True)):
            s1 = socket.create_connection(('127.0.0.1', t.port), timeout=5)
            s1.recv(64)
            s1.sendall(struct.pack('>I', len(body) + delta) + body)
            reply = s1.recv(64)
            s1.close()
            eq(b'CRUX-LANDED' in reply, want, f'framed send: {label}')
        ok(t.verdict()[0], 'the exact frame landed')
        got = t.record.requests[0].raw
        ok(got == body[:-1],
           'a short header truncates the recorded body, it does not just '
           'mis-score it')


def test_hostile_capstone() -> None:
    """crux D19: you can fail this one by pressing a key.

    The point of the scenario is that the broken script **works**. Anything
    that made it fail at the exploit as well would let a student conclude the
    lesson is "broken scripts are broken" rather than "working scripts can
    still be hostile", so that is asserted here explicitly.
    """
    from crux.screens.salvage import SalvageScreen
    from crux.screens.runresult import RunResultScreen

    caps = all_caps()[0]

    # 1. Run it unread: the exploit lands and the beacon fires anyway.
    session = Session.open(clock=FakeClock(), read_only=True)
    scr = SalvageScreen(session, session.registry.by_id('salvage-hostile'))
    try:
        ok(scr.sink is not None, 'the trap sink was opened')
        ok(scr.sink.url != scr.url, 'the sink is a different service')
        eq(scr.tripped, False, 'nothing has been sent yet')
        action = scr._run()
        ok(scr.tripped, 'running it unread trips the trap')
        ok(scr.target.verdict()[0],
           'and the exploit itself worked, which is why anyone would run it')
        eq(action.kind, 'replace', 'tripping the trap ends the scenario')
        res = action.screen
        ok(isinstance(res, RunResultScreen), 'it goes to the run result')
        ok(not res.score.landed,
           'a tripped trap is not a pass however well the exploit worked')
        eq(res.score.total_score, 0.0, 'and it scores zero')
        eq(res.tripped, True, 'the result screen knows')
        shown = ''.join(r.plain() for r in res.render(caps))
        ok('without reading it' in shown, 'and says so plainly')
        ok('/feed' in shown, 'and shows what the beacon sent')
        eq(session.state.attempts[0].read_first, False,
           'read_first recorded the failure (crux D19)')
    finally:
        scr.close()

    # 2. Read it, remove the beacon, run it: lands clean.
    session2 = Session.open(clock=FakeClock(), read_only=True)
    sc = session2.registry.by_id('salvage-hostile')
    scr2 = SalvageScreen(session2, sc)
    try:
        scr2.opened = True
        scr2.path.write_text(sc.body.render(sc.body.solution, scr2.url, 0,
                                            scr2.sink.url))
        action = scr2._run()
        ok(not scr2.tripped, 'the fixed script never contacts the sink')
        res = action.screen
        ok(res.score.landed, 'and it lands')
        eq(res.score.total_score, 100.0, 'for full marks')
        eq(session2.state.attempts[0].read_first, True,
           'opening it first is recorded too')
    finally:
        scr2.close()


def test_progress_reset_and_work_files() -> None:
    """Work survives a visit, re-points itself, and can be reset.

    Two bugs sat here before there was a reset at all: salvage rewrote your
    script from the original every time you opened the scenario, silently
    destroying your repairs, and conduit never rewrote it, so a mangled script
    could not be recovered. A reset is meaningless if the app is resetting your
    file behind your back anyway, so both are covered here.
    """
    import subprocess
    import tempfile

    from crux import progress
    from crux.screens.reset import ResetScreen
    from crux.screens.salvage import SalvageScreen
    from crux.scoring import score_run

    home = Path(tempfile.mkdtemp(prefix='crux-reset-'))
    real_home = os.environ['XDG_DATA_HOME']
    os.environ['XDG_DATA_HOME'] = str(home)
    try:
        session = Session.open(clock=FakeClock())
        sc = session.registry.by_id('salvage-py2')

        first = SalvageScreen(session, sc)
        first_url = first.url
        ok(first.path.exists(), 'the exercise file is written on first open')
        ok(not first.resumed, 'and the first open is not a resume')
        first.path.write_text(first.path.read_text() + '\n# MY REPAIR\n')
        first.close()

        second = SalvageScreen(session, sc)
        text = second.path.read_text()
        ok('# MY REPAIR' in text, 'your edits survive reopening the scenario')
        ok(second.resumed, 'and the screen says it resumed your file')
        ok(first_url != second.url, 'the mock target really does move port')
        ok(first_url not in text, 'the dead address was replaced')
        ok(second.url in text, 'with the one that answers now')

        # Restore takes two presses, and the first one only arms it.
        second.handle(K.parse('R'))
        ok(second.confirm_restore, 'one R arms the restore rather than doing it')
        ok(any('again' in h[1] for h in second.hints(all_caps()[0])),
           'and the footer says a second press is needed')
        second.handle(K.parse('ESC'))
        ok(not second.confirm_restore, 'esc disarms it')
        ok('# MY REPAIR' in second.path.read_text(), 'and changes nothing')

        second.handle(K.parse('R'))
        second.handle(K.parse('R'))
        restored = second.path.read_text()
        ok('# MY REPAIR' not in restored, 'two presses restore the original')
        ok(second.url in restored, 'and the original still points at the target')
        second.close()

        # A hardcoded address the scenario is *about* must not be re-pointed.
        addr = session.registry.by_id('salvage-address')
        a1 = SalvageScreen(session, addr)
        a1.path.write_text(addr.body.render(addr.body.solution, a1.url,
                                            int(a1._subs['port']), ''))
        a1.close()
        a2 = SalvageScreen(session, addr)
        kept = a2.path.read_text()
        # The solution keeps LHOST and LPORT as separate variables, so the
        # joined form only exists at runtime; both halves must survive.
        ok('"127.0.0.1"' in kept and '"4444"' in kept,
           'the collector address the exercise is about is left alone')
        subprocess.run([sys.executable, str(a2.path)], capture_output=True,
                       timeout=25)
        ok(a2.target.verdict()[0],
           'and a solved script still lands after being re-pointed')
        a2.close()

        # Reset, from the screen, needs two keys and then really erases.
        session.record_run(sc, score_run(True, 3, 3, 'ok', 1, True, 42.0))
        before = progress.summary(session.state)
        ok(before.attempts >= 1 and before.work_scenarios >= 1,
           'there is progress on disk to erase')

        rs = ResetScreen(session)
        rs.handle(K.parse('a'))
        ok(rs.pending == 'all', 'one key arms the reset')
        ok(Path(home / 'crux' / 'state.json').exists(),
           'and arming it erases nothing')
        rs.handle(K.parse('a'))
        ok(not (home / 'crux' / 'state.json').exists(), 'history is erased')
        ok(not (home / 'crux' / 'work').exists(), 'work files are erased')
        eq(session.state.attempts, [], 'and the live session forgets them too')
        ok('Erased' in ''.join(r.plain() for r in rs.render(all_caps()[0])),
           'the screen says what it did')

        after = progress.summary(session.state)
        ok(not after.anything, 'nothing is left')
        ok('nothing' in after.history_line() or 'no attempts'
           in after.history_line(), 'and the summary says so')
    finally:
        os.environ['XDG_DATA_HOME'] = real_home


def test_result_explains_every_key_line() -> None:
    """Every lead and every decoy must say what it meant.

    The score tells a student *that* they missed something or chased
    something; only `Line.why` tells them **why that line was the lead** or
    **why that one was a trap**, which is the entire thing the track teaches.
    A key line with no explanation is a teaching hole, so it is a failure
    rather than a style note.
    """
    from crux.screens.mark import MarkScreen
    from crux.screens.result import ResultScreen

    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    caps = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.UNICODE,
                  next(iter(PALETTES.values())), 88, 60)

    for sc in load().track('sift').scenarios:
        if not isinstance(sc.body, MarkBody):
            continue
        for ln in sc.body.build(0):
            if ln.kind in ('lead', 'decoy'):
                ok(bool(ln.why.strip()),
                   f'{sc.id}: {ln.kind} {ln.id!r} explains nothing')

        # And the explanation has to actually reach the result screen. Play it
        # badly on purpose: miss every lead and chase every decoy, which is
        # the attempt that most needs explaining.
        mark = MarkScreen(session, sc, seed=0)
        score = score_marks(mark.leads, mark.decoys, mark.decoys, elapsed=10.0)
        res = ResultScreen(session, sc, score, mark.lines)
        # content(), not render(): the result scrolls, so render() returns only
        # the visible window. What matters here is that the explanation is on
        # the screen at all; that it can be scrolled to is tested separately.
        # Whitespace-free, because wrapping legitimately breaks a line at a
        # real hyphen ("catch-all" -> "catch-" / "all") and a fragment compared
        # with spaces in it would fail on correct output.
        shown = ''.join(''.join(r.plain().split()) for r in res.content(caps))
        for ln in mark.lines:
            if ln.kind in ('lead', 'decoy') and ln.why:
                fragment = ''.join(ln.why.split())[:34]
                ok(fragment in shown,
                   f'{sc.id}: the explanation for {ln.id!r} never reaches the '
                   'result screen')
        # The verdict has to be a sentence, not just a band name.
        ok('Youmissed' in shown or 'nothinghere' in shown.lower(),
           f'{sc.id}: the result states the outcome in words')
        ok('Whatyouchased' in shown or not score.chased,
           f'{sc.id}: result groups what was chased under a heading')
        ok('Whatmattered' in shown or not (score.found or score.missed),
           f'{sc.id}: result groups what mattered under a heading')


def test_result_screens_scroll() -> None:
    """The debrief must be reachable on a minimum-size terminal.

    The height backstop truncates a body that does not fit, which is right as
    a backstop and wrong as the outcome here: the part that fell off the
    bottom of a result screen was the debrief, so on a 24-row terminal a
    student got the score and silently lost the explanation.
    """
    from crux.screens.mark import MarkScreen
    from crux.screens.result import ResultScreen

    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    small = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                   next(iter(PALETTES.values())), MIN_COLS, MIN_ROWS)

    # A greedy run, because that is the result that is actually long: every
    # chased line is listed, and the debrief sits under all of them. A perfect
    # score has nothing to list and fits in 24 rows, which is why the first
    # version of this test asserted an overflow that was not there.
    sc = session.registry.by_id('sift-nmap-dc')
    mark = MarkScreen(session, sc, seed=0)
    everything = {ln.id for ln in mark.lines}
    score = score_marks(mark.leads, mark.decoys, everything,
                        action_ok=False, has_action=True, elapsed=30.0)
    res = ResultScreen(session, sc, score, mark.lines,
                       chose=sc.body.actions[0])

    ok(res.scrollable(small), 'this result really does overflow 24 rows')
    ok(any(h[1] == 'scroll' for h in res.hints(small)),
       'and the footer offers scrolling only because it does')

    tail = sc.body.debrief.split()[-4:]
    seen = lambda: ' '.join(''.join(r.plain() for r in res.render(small)).split())
    ok(' '.join(tail) not in seen(), 'the end of the debrief starts off-screen')
    for _ in range(60):
        res.handle(K.parse('Down'))
    ok(' '.join(tail) in seen(), 'scrolling reaches the end of the debrief')
    for _ in range(200):
        res.handle(K.parse('Up'))
    eq(res.scroll, 0, 'scrolling back stops at the top')

    big = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                 next(iter(PALETTES.values())), MIN_COLS, 80)
    ok(not res.scrollable(big), 'a tall terminal needs no scrolling')
    ok(not any(h[1] == 'scroll' for h in res.hints(big)),
       'and is not offered a key that would do nothing')


def test_chain_flow() -> None:
    """Drive a whole engagement: sift the lead, salvage the exploit, pivot.

    This is chain mode's reason to exist, so it is verified the way it will be
    played: one continuous flow through the three real engines, ending on a
    recorded engagement. The conduit leg is skipped where namespaces are
    unavailable, the same honest degradation the standalone track uses.
    """
    from crux.screens.chain import (BridgeScreen, Chain, ChainIntroScreen,
                                    ChainResultScreen)
    from crux.targets import netns

    session = Session.open(clock=FakeClock(), read_only=True)
    sc = session.registry.by_id('chain-wexler')
    ok(isinstance(sc.body, ChainBody), 'the engagement is a ChainBody')
    eq(tuple(st.track for st in sc.body.stages), ('sift', 'salvage', 'conduit'),
       'the stages are the three tracks in engagement order')

    caps = all_caps()[0]
    intro = ChainIntroScreen(session, sc)
    ok(bool(intro.render(caps)), 'the intro renders')
    start = intro.handle(K.parse('RET'))
    eq(type(start.screen).__name__, 'MarkScreen', 'begin opens the sift stage')

    chain_obj = None

    # Stage 1: sift, played correctly.
    s1 = start.screen
    chain_ref = getattr(s1, 'on_done')
    lead = next(i for i, l in enumerate(s1.lines) if l.kind == 'lead')
    for _ in range(lead):
        s1.handle(K.parse('Down'))
    s1.handle(K.parse('SPC'))
    act = s1.handle(K.parse('RET')).screen
    eq(type(act).__name__, 'ActScreen', 'submitting the marks reaches the act beat')
    correct = next(i for i, a in enumerate(act.body_data.actions) if a.correct)
    for _ in range(correct):
        act.handle(K.parse('Down'))
    bridge1 = act.handle(K.parse('RET')).screen
    ok(isinstance(bridge1, BridgeScreen), 'a finished sift stage bridges on')
    eq(bridge1.stage.track, 'salvage', 'and the next stage is salvage')
    ok(bool(bridge1.render(caps)), 'the bridge renders')
    before = len(session.state.attempts)
    ok(before == 0, 'a chain stage does not record a standalone attempt')

    # Stage 2: salvage, fixed and landed.
    s2 = bridge1.handle(K.parse('RET')).screen
    eq(type(s2).__name__, 'SalvageScreen', 'the bridge opens the salvage stage')
    ok(s2.error == '', 'the salvage target opened inside the chain')
    s2.path.write_text(s2.body_data.render(s2.body_data.solution, s2.url, 0))
    bridge2 = s2.handle(K.parse('r')).screen
    ok(isinstance(bridge2, BridgeScreen), 'landing the exploit bridges on')
    eq(bridge2.stage.track, 'conduit', 'and the last stage is conduit')

    # Stage 3: conduit, if the kernel allows it.
    s3 = bridge2.handle(K.parse('RET')).screen
    eq(type(s3).__name__, 'ConduitScreen', 'the bridge opens the conduit stage')
    if s3.usable:
        s3.path.write_text(s3.body_data.render(s3.body_data.solution,
                                              str(s3.assets)))
        res = s3.handle(K.parse('r')).screen
    else:
        res = s3.handle(K.parse('RET')).screen   # skip an unverifiable leg
    ok(isinstance(res, ChainResultScreen), 'the last stage reaches the result')
    ok(bool(res.render(caps)), 'the engagement result renders')

    chain_attempts = [a for a in session.state.attempts if a.track == 'chain']
    eq(len(chain_attempts), 1, 'exactly one engagement attempt was recorded')
    eq(chain_attempts[0].scenario, 'chain-wexler', 'under the chain id')
    if s3.usable:
        eq(res.chain.passed, 3, 'a clean run passes all three stages')
        eq(chain_attempts[0].total, 100.0, 'and scores 100')
    ok('rooted' in ''.join(r.plain() for r in res.render(caps))
       or f'{res.chain.passed} of 3' in ''.join(r.plain()
                                                for r in res.render(caps)),
       'the result names how much of the box fell')


def test_chain_partial() -> None:
    """A stumble does not end the engagement, and the result is honest about it.

    Play the sift stage badly and the salvage stage by giving up, and the chain
    must still carry through to conduit and report which stages actually fell.
    """
    from crux.screens.chain import BridgeScreen, ChainIntroScreen

    session = Session.open(clock=FakeClock(), read_only=True)
    sc = session.registry.by_id('chain-wexler')
    intro = ChainIntroScreen(session, sc)
    s1 = intro.handle(K.parse('RET')).screen

    # Submit the sift stage marking nothing, then pick a wrong action.
    act = s1.handle(K.parse('RET')).screen
    wrong = next(i for i, a in enumerate(act.body_data.actions)
                 if not a.correct)
    for _ in range(wrong):
        act.handle(K.parse('Down'))
    bridge1 = act.handle(K.parse('RET')).screen
    ok(isinstance(bridge1, BridgeScreen),
       'a fumbled sift stage still bridges on rather than blocking')

    # Salvage: give up without landing.
    s2 = bridge1.handle(K.parse('RET')).screen
    s2.runs = 1                              # enable give-up
    nxt = s2.handle(K.parse('g'))
    ok(nxt.kind == 'replace', 'giving up on the exploit advances the chain')
    ok(isinstance(nxt.screen, BridgeScreen) or
       type(nxt.screen).__name__ == 'ChainResultScreen',
       'to the pivot or the result, never a dead end')


def test_list_windowing() -> None:
    """The selected item must stay on screen through a full traversal.

    This is the regression guard for a real bug: the list scrolled in rows
    while the cursor counted items, and screens that draw two rows per item let
    the selection descend twice as fast as the window and run off the bottom,
    so pressing down did nothing selectable. The window is measured in item
    blocks now, and this walks every item at cramped heights to prove the
    selector never disappears.
    """
    from crux.screens.home import HomeScreen
    from crux.screens.track import TrackScreen

    session = Session.open(clock=FakeClock(), read_only=True)

    def selector_visible(scr, caps) -> bool:
        return any(caps.g('sel') in t.plain() for t in scr.render(caps))

    for make in (lambda: HomeScreen(session),
                 lambda: TrackScreen(session, 'sift'),      # 26 items
                 lambda: TrackScreen(session, 'salvage'),
                 lambda: TrackScreen(session, 'conduit')):
        for rows in (10, 12, 16, 20, 24):
            caps = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.UNICODE,
                          next(iter(PALETTES.values())), 80, rows)
            scr = make()
            n = scr.count()
            for _ in range(n + 2):        # a full loop plus wrap-around
                ok(selector_visible(scr, caps),
                   f'{type(scr).__name__} @80x{rows}: selector visible at '
                   f'cursor {scr.cursor}/{n}')
                for r in scr.render(caps):
                    ok(r.width() <= caps.cols,
                       f'{type(scr).__name__} @80x{rows}: row fits')
                scr.handle(K.parse('Down'))
            # End and Home land on a visible selection too
            scr.handle(K.parse('End'))
            ok(selector_visible(scr, caps),
               f'{type(scr).__name__} @80x{rows}: End keeps the selector shown')
            scr.handle(K.parse('Home'))
            ok(selector_visible(scr, caps),
               f'{type(scr).__name__} @80x{rows}: Home keeps the selector shown')


def test_home_shows_composites() -> None:
    """The picker lists the skill tracks, then every composite with content.

    Asserted by name rather than by row number. The picker used to index into
    `SECTIONS`, which is correct only while every composite has content: an
    empty one is not shown, and from that point every index below it names the
    wrong track. Pinning the *names* is what makes that class of bug fail here
    rather than in somebody's hands.
    """
    from crux.config import COMPOSITE
    from crux.screens.home import HomeScreen
    session = Session.open(clock=FakeClock(), read_only=True)
    home = HomeScreen(session)
    caps = all_caps()[0]

    live = [n for n in COMPOSITE if session.registry.track(n).scenarios]
    eq(home.count(), len(TRACKS) + len(live),
       'the skill tracks plus every composite that has content')
    eq(home._names(), list(TRACKS) + live, 'in that order')

    shown = ''.join(r.plain() for r in home.render(caps))
    ok('chain' in shown, 'chain is on the picker')
    ok('capstone' in shown, 'and marked as the capstone')
    ok('proctor' in shown, 'proctor is on the picker')
    ok('timed' in shown, 'and marked as the timed one')

    for i, name in enumerate(home._names()):
        opened = home.activate(i)
        eq(type(opened.screen).__name__, 'TrackScreen', f'row {i} opens')
        eq(opened.screen.track_name, name, f'row {i} opens {name}')


def test_conduit_engine() -> None:
    """The namespace engine, including the honest degradation of crux D14."""
    import tempfile

    from crux.screens.conduit import ConduitScreen
    from crux.targets import netns

    usable, why = netns.capability()
    ok(isinstance(usable, bool) and isinstance(why, str),
       'capability() answers with a verdict and a reason')
    ok(usable or why, 'and when it says no it says why')

    reg = load()
    conduits = [s for s in reg.track('conduit').scenarios
                if isinstance(s.body, ConduitBody)]
    ok(len(conduits) >= 7, f'{len(conduits)} conduit scenarios')
    # The whole point of the track is topology variety, not one shape reused.
    shapes = {(len(sc.body.topology.hosts), len(sc.body.topology.links))
              for sc in conduits}
    ok(len(shapes) >= 3, 'the topologies genuinely differ in shape')
    socks = [sc for sc in conduits
             if any(pr.socks for pr in sc.body.topology.probes)]
    ok(bool(socks), 'at least one scenario verifies through a SOCKS proxy')
    for sc in conduits:
        b = sc.body
        eq(sc.tier, 'verified', f'{sc.id}: conduit is verified')
        ok(b.starter != b.solution, f'{sc.id}: the pair differs')
        ok(bool(b.topology.probes), f'{sc.id}: has something to verify')
        ok(bool(b.topology.negative),
           f'{sc.id}: proves the target is out of reach to begin with')
        rendered = b.render(b.starter, '/tmp/assets')
        ok('{{ASSETS}}' not in rendered, f'{sc.id}: assets path substituted')

    assets = netns.prepare_assets(Path(tempfile.mkdtemp()) / 'a')
    for want in ('id', 'id.pub', 'hostkey', 'sshd_config', 'svc.py',
                 'etc/passwd', 'etc/shadow', 'empty'):
        ok((assets / want).exists(), f'prepare_assets makes {want}')
    ok(netns.prepare_assets(assets) == assets, 'prepare_assets is idempotent')
    before = (assets / 'id').read_bytes()
    netns.prepare_assets(assets)
    eq((assets / 'id').read_bytes(), before,
       'and does not regenerate a key a student has already referenced')

    # A needs-gated scenario is intercepted before the engine screen: it names
    # the missing tool and scores nothing, rather than trying to build a
    # topology that cannot run.
    from crux.model import missing_needs
    from crux.screens.track import NeedsScreen
    gated = [sc for sc in conduits if sc.needs]
    ok(bool(gated), 'some conduit scenarios declare tool needs')
    gsession = Session.open(clock=FakeClock(), read_only=True)
    chisel = load().by_id('conduit-agent')
    if 'chisel' in missing_needs(chisel):
        ns = NeedsScreen(gsession, chisel, missing_needs(chisel))
        caps0 = all_caps()[0]
        shown = ''.join(r.plain() for r in ns.render(caps0))
        ok('chisel' in shown, 'the needs screen names the missing tool')
        ok('not scored' in shown or 'Nothing here is scored' in shown,
           'and scores nothing')
        before = len(gsession.state.attempts)
        for chord in ('r', 'e', 'RET'):
            ns.handle(K.parse(chord))
        eq(len(gsession.state.attempts), before,
           'a needs-gated scenario records nothing')

    # crux D14: with namespaces unavailable, the screen says so and scores
    # nothing rather than pretending.
    session = Session.open(clock=FakeClock(), read_only=True)
    real = netns.capability
    import crux.screens.conduit as cs
    cs.capability = lambda: (False, 'unprivileged_userns_clone is 0')
    try:
        scr = cs.ConduitScreen(session, conduits[0])
        caps = all_caps()[0]
        ok(not scr.usable, 'the screen knows it cannot verify')
        shown = ''.join(r.plain() for r in scr.render(caps))
        ok('cannot verify' in shown, 'and says so on the screen')
        ok('unprivileged_userns_clone' in shown, 'quoting the actual reason')
        ok(not any(h[0] == 'r' for h in scr.hints(caps)),
           'and does not offer a run key that would do nothing')
        before_n = len(session.state.attempts)
        for chord in ('r', 'e', 'RET', 'g'):
            scr.handle(K.parse(chord))
        eq(len(session.state.attempts), before_n,
           'an unusable track records nothing at all')
        scr.close()
    finally:
        cs.capability = real


def test_all_conduit_solutions() -> None:
    """Every buildable conduit solution opens its path; every starter fails.

    This is the run check from `validate.py`, in `test.py` so a green test run
    means the whole track is solvable and honestly broken, not only the two
    scenarios the end-to-end test drives. Gated and unavailable scenarios are
    skipped, not failed.
    """
    import tempfile

    from crux.model import missing_needs
    from crux.targets import netns

    usable, why = netns.capability()
    if not usable:
        ok(True, f'conduit solutions skipped: {why}')
        return

    conduits = [s for s in load().track('conduit').scenarios
                if isinstance(s.body, ConduitBody) and not missing_needs(s)]
    work = Path(tempfile.mkdtemp(prefix='crux-test-allcond-'))
    assets = netns.prepare_assets(work / 'assets')
    for sc in conduits:
        b = sc.body
        path = work / b.filename
        path.write_text(b.render(b.solution, str(assets)))
        good = netns.run_attempt(b.topology, path, assets, b.settle)
        ok(good.ok, f'{sc.id}: solution opens the path '
                    f'({good.detail or good.error})')
        path.write_text(b.render(b.starter, str(assets)))
        bad = netns.run_attempt(b.topology, path, assets, b.settle)
        ok(not bad.ok, f'{sc.id}: the starter does not')


def test_conduit_end_to_end() -> None:
    """Actually build a network and open a path through it.

    Skips cleanly where the kernel will not allow it, which is the same crux
    D14 rule the app follows: better to say nothing than to claim a check that
    did not happen.
    """
    import tempfile

    from crux.targets import netns

    usable, why = netns.capability()
    if not usable:
        print(f'  note  conduit end-to-end skipped: {why}')
        ok(True, 'conduit skipped honestly where namespaces are unavailable')
        return

    sc = load().by_id('conduit-forward')
    b = sc.body
    work = Path(tempfile.mkdtemp(prefix='crux-test-conduit-'))
    assets = netns.prepare_assets(work / 'assets')
    path = work / b.filename

    path.write_text(b.render(b.solution, str(assets)))
    good = netns.run_attempt(b.topology, path, assets, b.settle)
    ok(good.ok, f'the reference tunnel opens the path ({good.detail or good.error})')
    eq(good.met, good.total, 'every probe answered')

    path.write_text(b.render(b.starter, str(assets)))
    bad = netns.run_attempt(b.topology, path, assets, b.settle)
    ok(not bad.ok, 'the starter does not')
    ok('did not answer' in bad.detail or bad.error,
       'and the failure names what did not answer')


def test_no_third_party_attribution() -> None:
    """Nothing the program shows may name a training platform or a machine.

    crux D23: the exercises stand on the technique being real and, where one
    applies, on the CVE. Naming somebody else's course, lab or box adds
    nothing a student can use and quietly stops crux being handable to anyone.
    The `source` field still records where a scenario came from, because
    `validate.py` audits it, but it is authoring metadata and is never
    rendered.

    This walks every string any screen can display, which is the only way to
    keep it true as content grows.
    """
    import re

    from crux.model import ChainBody, ConduitBody, MarkBody, SalvageBody
    from crux.provenance import based_on

    banned = re.compile(
        r'hackthebox|\bhtb\b|proving\s?ground|vulnlab|prolabs|pen-?200|'
        r'\boscp\b|offsec|\.vl\b|'
        r'\b(cicada|busqueda|nibbles|monitored|lavita|updown|markup|jacko|'
        r'cereal|jeeves|siteisup|searcher|hollow)\b', re.I)

    def strings(sc):
        b = sc.body
        out = [sc.title, based_on(sc.source)]
        if isinstance(b, MarkBody):
            out += [b.prompt, b.debrief]
            out += [l.text for l in b.canonical()]
            out += [a.text for a in b.actions] + [a.why for a in b.actions]
        elif isinstance(b, SalvageBody):
            out += [b.brief, b.debrief, b.real_note, b.models, b.cve,
                    b.broken, b.solution]
        elif isinstance(b, ConduitBody):
            out += [b.brief, b.debrief, b.starter, b.solution]
        elif isinstance(b, ChainBody):
            out += [b.brief, b.debrief]
            for st in b.stages:
                out += [st.bridge, st.title]
        return out

    for sc in load().scenarios:
        for text in strings(sc):
            hit = banned.search(text or '')
            ok(hit is None,
               f'{sc.id}: displayed text names a third party '
               f'({hit.group(0) if hit else ""})')

    # The label itself must be one of the two non-attributing forms.
    from crux.provenance import FROM_CHAIN, FROM_TRADECRAFT
    for sc in load().scenarios:
        if sc.source:
            ok(based_on(sc.source) in (FROM_CHAIN, FROM_TRADECRAFT),
               f'{sc.id}: provenance label is non-attributing')

    # And the help screen, which is where the question gets answered.
    from crux.screens.help import HelpScreen
    caps = all_caps()[0]
    for topic in (None, 'sift', 'salvage', 'conduit', 'chain'):
        shown = ''.join(r.plain() for r in HelpScreen(topic).render(caps))
        hit = banned.search(shown)
        ok(hit is None,
           f'help({topic}) names a third party ({hit.group(0) if hit else ""})')


def test_splash() -> None:
    """The launch and exit sequences: every rung, and the guards.

    A splash that could throw would be the one thing able to fail a launch, so
    the whole point of the checks is that it never does and always degrades.
    """
    from crux import splash as SP

    # It renders at every rung, fits the documented minimum, and the ASCII
    # rung stays pure ASCII: a screen of tofu is not an entrance.
    for caps in all_caps(SP.MIN_COLS, SP.MIN_ROWS):
        for step in range(SP.STEPS):
            rows = SP.frame(caps, step, note='26 sift  10 salvage')
            ok(bool(rows), 'the intro frame renders')
            for r in rows:
                ok(r.width() <= caps.cols,
                   f'intro line of {r.width()} exceeds {caps.cols}')
        for step in range(SP.OUT_STEPS):
            for r in SP.out_frame(caps, step):
                ok(r.width() <= caps.cols, 'outro line fits')
        for r in SP.farewell_frame(caps):
            ok(r.width() <= caps.cols, 'farewell line fits')
        if caps.glyphs is R.GlyphLevel.ASCII:
            for producer in (SP.frame(caps, SP.STEPS - 1, hold=True),
                             SP.out_frame(caps, 0), SP.farewell_frame(caps)):
                plain = ''.join(r.plain() for r in producer)
                ok(plain.isascii(),
                   'the splash ASCII rung carries no non-ASCII')

    # The scope is a real animation: the first frame is mostly noise floor,
    # the last is a clean locked peak, and they differ. The locked frame is
    # deterministic (the noise term is gone at full progress), so the peak is
    # stable while the entrance is held rather than flickering.
    caps = R.Caps(R.ColorLevel.TRUE, R.GlyphLevel.UNICODE,
                  next(iter(PALETTES.values())), 80, 22)
    first = ''.join(r.plain() for r in SP.frame(caps, 0))
    last = ''.join(r.plain() for r in SP.frame(caps, SP.STEPS - 1))
    ok(first != last, 'the entrance animates rather than snapping')
    ok(''.join(r.plain() for r in SP.frame(caps, SP.STEPS - 1))
       == last, 'the locked frame is stable, not random, while held')
    ok('locked' in last and 'scanning' in first,
       'the status reads scanning while acquiring and locked at the end')
    # The locked frame is the whole wordmark: every bold-art line is present.
    locked = [r.plain() for r in SP.frame(caps, SP.STEPS - 1)]
    for art_line in SP.WORD_BOLD:
        ok(any(art_line in r for r in locked),
           'the locked frame renders the full CRUX wordmark')
    # The sweep is directional: the left of the word locks before the right.
    early = SP.frame(caps, 3)
    left = sum(r.plain()[:len(r.plain()) // 2].count('\u2588') for r in early)
    right = sum(r.plain()[len(r.plain()) // 2:].count('\u2588') for r in early)
    ok(left > right,
       'early in the sweep the left of the word is more resolved than the right')

    # It degrades: too small to fit means it does not play at all.
    ok(SP.fits(caps), 'a big enough window fits the splash')
    ok(not SP.fits(R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                          next(iter(PALETTES.values())), 20, 6)),
       'a tiny window does not')

    # The scope note is computed from the registry and never throws.
    note = SP.scope_note(load())
    ok('sift' in note and 'chain' in note,
       'the scope note names the sections that loaded')

    # play() and outro() drive a fake terminal without a real one, and neither
    # raises. This is the guarantee that matters: an entrance cannot be the
    # thing that fails a launch.
    class _FakeTty:
        def __init__(self): self.writes = 0
        def write(self, s): self.writes += 1
        def read_keys(self, timeout=None): return []
    t1 = _FakeTty()
    SP.play(t1, caps, note=note, hold=False)
    ok(t1.writes > 0, 'play writes frames to the terminal')
    t2 = _FakeTty()
    SP.outro(t2, caps, hold=0.0)
    ok(t2.writes > 0, 'outro writes frames to the terminal')

    class _AngryTty:
        def write(self, s): raise OSError('terminal went away')
        def read_keys(self, timeout=None): raise OSError('gone')
    SP.play(_AngryTty(), caps, hold=False)
    SP.outro(_AngryTty(), caps, hold=0.0)
    ok(True, 'a terminal that throws on every call does not crash the splash')


def test_screen_contract() -> None:
    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    caps = all_caps()[0]
    for scr in _screens(session):
        name = type(scr).__name__
        hints = scr.hints(caps)
        ok(bool(hints), f'{name}: declares key hints')
        ok(any(h[0] in ('q', 'esc') for h in hints),
           f'{name}: advertises a way out')
        ok(bool(scr.body(caps)) or hasattr(scr, 'rows'),
           f'{name}: is never blank')
        scr.close()
        scr.close()  # close is idempotent by contract
        ok(True, f'{name}: close is idempotent')
    ok(HomeScreen(session).can_pop is False, 'the root screen does not pop')


def test_walkthrough() -> None:
    """Drive the real stack with real keys, picker to recorded result."""
    clock = FakeClock()
    session = Session.open(clock=clock, read_only=True, seed_override=0)
    stack: list[Screen] = [HomeScreen(session)]
    caps = all_caps()[0]

    def press(chord: str) -> None:
        key = K.parse(chord)
        action = stack[-1].handle(key)
        if action.kind == 'push':
            stack.append(action.screen)
        elif action.kind == 'replace':
            stack.pop().close()
            stack.append(action.screen)
        elif action.kind == 'pop' and len(stack) > 1:
            stack.pop().close()
        elif action.kind == 'root':
            while len(stack) > 1:
                stack.pop().close()

    eq(type(stack[-1]).__name__, 'HomeScreen', 'starts at the picker')
    press('RET')                                   # into sift
    eq(type(stack[-1]).__name__, 'TrackScreen', 'entered a track')
    press('RET')                                   # into the scenario
    eq(type(stack[-1]).__name__, 'MarkScreen', 'opened the scenario')

    mark = stack[-1]
    lead_index = next(i for i, l in enumerate(mark.lines) if l.kind == 'lead')
    lead_id = mark.lines[lead_index].id
    clock.advance(45)
    for _ in range(lead_index):
        press('Down')
    press('SPC')
    eq(mark.marked, {lead_id}, 'space marks the line under the cursor')
    press('SPC')
    eq(mark.marked, set(), 'space toggles back off')
    press('SPC')
    ok(bool(mark.render(caps)), 'the marking screen still renders after input')

    press('RET')                                   # submit, into the act beat
    eq(type(stack[-1]).__name__, 'ActScreen', 'submitting reaches the act beat')
    clock.advance(15)
    correct = next(i for i, a in enumerate(mark.body_data.actions) if a.correct)
    for _ in range(correct):
        press('Down')
    press('RET')

    eq(type(stack[-1]).__name__, 'ResultScreen', 'choosing reaches the result')
    eq(len(session.state.attempts), 1, 'exactly one attempt was recorded')
    a = session.state.attempts[0]
    eq(a.scenario, 'sift-nmap-pinned', 'the right scenario was recorded')
    eq(a.total, 100.0, 'a perfect run scores 100 end to end')
    eq(a.elapsed, 60.0, 'time on task spans both beats (crux D12)')
    ok(a.elapsed > 45.0, 'the act beat is not billed as free time')
    eq(a.marked, (lead_id,), 'the marks were stored, not just the score')
    eq(a.seed, 0, 'the seed that built the screen was recorded (crux D10)')
    eq(a.tier, 'graded', 'the tier was recorded')
    ok(bool(stack[-1].render(caps)), 'the result screen renders')

    press('H')                                     # home from three deep
    eq(type(stack[-1]).__name__, 'HomeScreen', 'H unwinds to the picker')
    eq(len(stack), 1, 'the stack really unwound')


def test_stub_records_nothing() -> None:
    """crux D6: a track with no engine must not write a score."""
    from crux.model import StubBody
    from crux.screens.stub import StubScreen
    session = Session.open(clock=FakeClock(), read_only=True)
    before = len(session.state.attempts)
    placeholder = Scenario(id='stub-probe', track='conduit', tier='self',
                           title='Engine not built yet',
                           body=StubBody(prompt='a future track lands here',
                                         phase='Phase 8', debrief='not yet'))
    scr = StubScreen(session, placeholder)
    caps = all_caps()[0]
    for chord in ('RET', 'SPC', 'a', 'Down'):
        scr.handle(K.parse(chord))
    ok(bool(scr.render(caps)), 'the stub screen renders')
    eq(len(session.state.attempts), before,
       'an unbuilt track records nothing at all')


def test_session_persists() -> None:
    session = Session.open(clock=FakeClock(), seed_override=0)
    sift = session.registry.by_id('sift-nmap-pinned')
    lines = sift.body.build(0)
    leads, decoys = roles(lines)
    score = score_marks(leads, decoys, leads, elapsed=12.0)
    session.record(sift, score, tuple(sorted(leads)), 0)
    eq(session.save_error, '', 'a normal save reports no error')
    reloaded = State.load()
    ok(any(a.scenario == 'sift-nmap-pinned' for a in reloaded.attempts),
       'a recorded attempt survives a reload')


def test_panning() -> None:
    """Real tool output is wider than a terminal; the tell can be at the end."""
    from crux.screens.mark import MarkScreen
    session = Session.open(clock=FakeClock(), read_only=True, seed_override=0)
    sc = session.registry.by_id('sift-nmap-dc')
    scr = MarkScreen(session, sc, seed=0)
    # Tall enough that every line is on screen at once. At 24 rows the list
    # windows on the cursor and the longest line sits below the fold, so a
    # panning assertion would be measuring the vertical window instead.
    caps = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                  next(iter(PALETTES.values())), MIN_COLS, 40)

    widest = max(len(l.text) for l in scr.lines)
    ok(widest > scr._text_budget(caps),
       'this fixture really does overflow 80 columns')
    ok(any(h[1] == 'pan' for h in scr.hints(caps)),
       'the footer offers panning when a line is clipped')

    visible = lambda: ''.join(r.plain() for r in scr.render(caps))
    tail = max(scr.lines, key=lambda l: len(l.text)).text[-12:]
    ok(tail not in visible(), 'the tail of the longest line starts hidden')
    for _ in range(40):
        scr.handle(K.parse('Right'))
        scr.render(caps)
    ok(tail in visible(), 'panning reaches the end of the longest line')
    eq(scr.hscroll, widest - scr._text_budget(caps),
       'panning clamps at the overflow rather than scrolling into space')
    for _ in range(40):
        scr.handle(K.parse('Left'))
    scr.render(caps)
    eq(scr.hscroll, 0, 'panning back stops at zero')

    narrow = R.Caps(R.ColorLevel.NONE, R.GlyphLevel.ASCII,
                    next(iter(PALETTES.values())), 200, 40)
    scr.hscroll = 999
    scr.render(narrow)
    ok(scr.hscroll <= max(0, widest - scr._text_budget(narrow)),
       'a resize to a wider terminal re-clamps the pan')


# --------------------------------------------------------------------------
# proctor
# --------------------------------------------------------------------------

def test_pacing_arithmetic() -> None:
    """The numbers `proctor` reports, checked without a screen in the way.

    Every claim the post-mortem makes is arithmetic, and arithmetic that is
    only ever seen through a rendered screen is arithmetic nobody has checked.
    """
    from crux import pacing

    a = pacing.allocations(('sift', 'salvage', 'conduit'), 2100.0)
    eq([round(x) for x in a], [300, 900, 900],
       'the budget splits by track weight')
    eq(round(sum(pacing.allocations(('sift',) * 7, 1000.0))), 1000,
       'the shares always sum back to the budget')
    eq(pacing.allocations((), 600.0), (), 'no slots, no shares')

    landed = pacing.Leg('a', 'sift', 'A', 300.0, 120.0, 100.0, reached=True)
    over = pacing.Leg('b', 'salvage', 'B', 600.0, 900.0, 0.0, reached=True)
    early = pacing.Leg('c', 'sift', 'C', 300.0, 60.0, 0.0, reached=True,
                       abandoned=True)
    late = pacing.Leg('d', 'sift', 'D', 300.0, 500.0, 0.0, reached=True,
                      abandoned=True)
    never = pacing.Leg('e', 'conduit', 'E', 600.0)

    eq(landed.overrun, 0.0, 'a leg inside its share has no overrun')
    eq(landed.sunk, 0.0, 'and nothing sunk')
    eq(over.overrun, 300.0, 'overrun is time past the share')
    eq(over.sunk, 300.0, 'and it is sunk when the leg scored nothing')
    eq(early.sunk, 0.0,
       'walking away inside the share sinks nothing, with no special case')
    eq(late.sunk, 200.0, 'walking away late still sinks what it cost')
    eq(never.overrun, 0.0, 'a leg you never reached cost no clock')
    eq(never.sunk, 0.0, 'and sank none')
    eq(landed.verdict, 'landed', 'verdicts read as English')
    eq(over.verdict, 'nothing for it', '...')
    eq(early.verdict, 'walked away', '...')
    eq(never.verdict, 'never reached', '...')

    paid_over = pacing.Leg('f', 'salvage', 'F', 600.0, 900.0, 100.0,
                           reached=True)
    eq(paid_over.overrun, 300.0, 'a leg that overran and landed still overran')
    eq(paid_over.sunk, 0.0,
       'but it bought something, so none of it is sunk (the crux D8 habit: '
       'only charge for what actually cost you)')

    r = pacing.review([landed, over, never], 1500.0, 70.0, spent=1100.0)
    eq(round(r.score, 1), 33.3, 'the score averages over every slot, reached '
                                'or not')
    ok(not r.passed, 'and it is short of the target')
    eq(r.spent, 1100.0, 'spent is the wall clock, not the sum of the legs')
    eq(r.on_legs, 1020.0, 'the legs account for less than the sitting did')
    eq(r.banked, 400.0, 'banked is what was left of the budget')
    eq(r.overspent, 0.0, 'and nothing ran past it')
    eq(r.sunk, 300.0, 'sunk rolls up across the legs')
    eq(len(r.unreached), 1, 'one leg was never reached')
    eq(len(r.landed), 1, 'one leg paid')
    eq(len(r.dry), 1, 'one was ridden to the end for nothing')

    over_budget = pacing.review([over], 600.0, 50.0, spent=900.0)
    eq(over_budget.overspent, 300.0, 'a sitting can end past its budget')
    eq(over_budget.banked, 0.0, 'and then nothing is banked')

    clean = pacing.review(
        [pacing.Leg('a', 'sift', 'A', 300.0, 100.0, 100.0, reached=True),
         pacing.Leg('b', 'sift', 'B', 300.0, 100.0, 100.0, reached=True)],
        600.0, 70.0, spent=200.0)
    ok(clean.passed, 'landing everything passes')
    ok('Cleared' in clean.headline(), 'and the headline says so')
    eq(clean.sunk, 0.0, 'with nothing sunk')
    eq(clean.notes(), ('Nothing to correct: every leg came in on its share.',),
       'a clean sitting gets one note and not a lecture')

    eq(len(r.sank), 1, 'one leg actually sank time')
    sank_and_walked = pacing.review([landed, late], 1500.0, 70.0, spent=620.0)
    eq(len(sank_and_walked.dry), 0,
       'a leg you walked away from was not ridden to the end')
    eq(len(sank_and_walked.sank), 1,
       'but it still sank the time it spent past its share, so the two '
       'populations are not the same set')
    ok('on 1 leg that scored zero' in ' '.join(sank_and_walked.notes()),
       'and the note counts the legs that sank, not the ones that were '
       'ridden out; counting the wrong set printed "14m 40s ... on 0 legs"')

    notes = ' '.join(r.notes())
    ok('past your own allocation' in notes, 'the sunk note is the first one')
    ok('abandoned nothing' in notes,
       'and riding a dead leg to the end is named')
    ok('Never reached' in notes, 'as are the legs the clock ate')

    walked = pacing.review([landed, early, never], 1500.0, 70.0, spent=500.0)
    ok(any('inside its' in n for n in walked.notes()),
       'an early walk-away is credited, not scolded')
    walked_late = pacing.review([landed, late, never], 1500.0, 70.0, spent=900.0)
    ok(any('came late' in n for n in walked_late.notes()),
       'a late one is credited and dated')

    eq(pacing.family('sift-nmap-pinned'), 'nmap', 'family reads the id')
    eq(pacing.family('proctor-short'), 'proctor-short',
       'an id with no family segment is its own family')


def test_pacing_history() -> None:
    """The standalone review folds every attempt, and never double-counts."""
    from crux import pacing

    rows = [
        Attempt('sift-a', 'sift', when=1.0, elapsed=100.0, total=90.0,
                marks=90.0, recall=1.0, precision=1.0, tier='graded'),
        Attempt('sift-b', 'sift', when=2.0, elapsed=300.0, total=0.0,
                marks=0.0, recall=0.0, precision=0.0, tier='graded'),
        Attempt('salvage-a', 'salvage', when=3.0, elapsed=600.0, total=0.0,
                marks=0.0, recall=0.0, precision=0.0, tier='verified',
                runs=3, read_first=False),
        Attempt('proctor-short', 'proctor', when=4.0, elapsed=1000.0,
                total=45.0, marks=45.0, recall=0.5, precision=0.8,
                tier='graded', sitting='proctor-short'),
    ]
    h = pacing.history(rows)
    eq(h.attempts, 3, 'the sitting summary is not one of the attempts')
    eq(h.total_time, 1000.0,
       'and its elapsed time is not added to the legs it contains')
    eq(h.zero_time, 900.0, 'time that bought nothing is summed')
    eq(round(h.zero_share, 2), 0.9, 'and expressed as a share')
    eq(h.sittings, 1, 'the sitting is counted as a sitting')
    eq(h.ran_unread, 1, 'running an unread proof-of-concept is counted')
    eq(h.longest.scenario, 'salvage-a', 'the longest single attempt is named')

    by = {t.track: t for t in h.tracks}
    eq(by['sift'].attempts, 2, 'per-track counts')
    eq(by['sift'].median, 200.0, 'per-track medians')
    eq(by['sift'].completed, 2, 'and how many of them were played out')
    eq(by['sift'].zeros, 1, 'per-track zero counts')
    eq(by['conduit'].attempts, 0, 'a track with no play is still listed')
    ok(by['sift'].thin, 'two attempts is below the sample floor')

    # An attempt you walked away from is time you spent, but it is not
    # evidence about how long the work takes, so it counts in one column and
    # not the other.
    walked = pacing.history(rows + [
        Attempt('sift-c', 'sift', when=5.0, elapsed=20.0, total=0.0,
                marks=0.0, recall=0.0, precision=0.0, tier='graded',
                sitting='proctor-short', abandoned=True)])
    w = {t.track: t for t in walked.tracks}['sift']
    eq(w.attempts, 3, 'a walk-away is an attempt')
    eq(w.completed, 2, 'but not a completed one')
    eq(w.median, 200.0,
       'so it does not drag the median of how long the work takes')
    eq(w.on_task, 420.0, 'while the time it cost is still counted')
    eq(walked.abandons, 1, 'and it is counted as a walk-away')

    empty = pacing.history([])
    ok(not empty.any, 'an empty history knows it is empty')
    ok('Nothing recorded yet' in empty.notes()[0], 'and says so once')


def test_sitting_fill() -> None:
    """Slot selection: unseen first, then spread, then least recently played."""
    from crux import pacing
    from crux.model import SittingBody, Slot

    reg = load()
    sit = reg.by_id('proctor-standard')
    ok(isinstance(sit.body, SittingBody), 'a sitting carries a SittingBody')

    fresh = State()
    picks = pacing.fill(sit.body.slots, reg, fresh)
    eq([p.track for p in picks], [s.track for s in sit.body.slots],
       'every slot draws from its own track')
    eq(len(set(p.id for p in picks)), len(picks),
       'and no scenario fills two slots')
    eq(pacing.fill(sit.body.slots, reg, fresh), picks,
       'selection is deterministic given a history')

    sifts = [pacing.family(p.id) for p in picks if p.track == 'sift']
    eq(len(set(sifts)), len(sifts),
       'the sift legs come from different families rather than three of the '
       'same')

    # Playing what it would have picked moves the selection on.
    played = State()
    played.record(Attempt(picks[0].id, picks[0].track, when=10.0, elapsed=60.0,
                          total=100.0, marks=100.0, recall=1.0, precision=1.0,
                          tier='graded'))
    moved = pacing.fill(sit.body.slots, reg, played)
    ok(moved[0].id != picks[0].id, 'a scenario you have played is not first')

    # With everything played, oldest wins and the slots still fill.
    everything = State()
    for i, sc in enumerate(reg.scenarios):
        everything.record(Attempt(sc.id, sc.track, when=5000.0 - i,
                                  elapsed=60.0, total=50.0, marks=50.0,
                                  recall=0.5, precision=0.5, tier=sc.tier))
    full = pacing.fill(sit.body.slots, reg, everything)
    ok(all(p is not None for p in full),
       'every slot still fills when nothing is unseen')
    oldest = min((s for s in reg.track('sift').scenarios),
                 key=lambda s: everything.last_when(s.id))
    eq(full[0].id, oldest.id, 'and the least recently played one comes first')

    # A tool you do not have is skipped rather than handed to you.
    gated = [s for s in reg.track('conduit').scenarios
             if s.needs and 'chisel' in s.needs]
    if gated:
        only_gated = (Slot(track='conduit', pool=(gated[0].id,)),)
        eq(pacing.fill(only_gated, reg, State()), (None,),
           'a slot that can only draw an uninstallable scenario yields None '
           'rather than an unplayable leg')


def test_sitting_flow() -> None:
    """Drive a whole sitting: play a leg, walk away from one, run past the
    budget, and land on the post-mortem.

    The one flow that exercises everything this track added: the shared clock,
    the abandon verb wired through the base screen, the per-leg recording, the
    budget deciding when the sitting ends, and the pacer being released after.
    """
    import crux.screens as SCR
    from crux.model import SittingBody
    from crux.screens.proctor import (BetweenScreen, SittingIntroScreen,
                                      SittingResultScreen)

    clock = FakeClock()
    session = Session.open(clock=clock, read_only=True)
    sc = session.registry.by_id('proctor-short')
    ok(isinstance(sc.body, SittingBody), 'proctor-short is a sitting')
    caps = all_caps()[0]

    intro = SittingIntroScreen(session, sc)
    ok(bool(intro.render(caps)), 'the intro renders')
    shown = ''.join(r.plain() for r in intro.render(caps))
    ok('compressed' in shown,
       'and says on its face that this is not a 24-hour exam (crux D14)')
    ok(not intro.unfillable, 'every leg has a scenario')
    ok(SCR.PACER is None, 'no clock is running before you press enter')

    leg1 = intro.handle(K.parse('RET')).screen
    eq(type(leg1).__name__, 'MarkScreen', 'enter opens the first leg')
    ok(SCR.PACER is not None, 'and starts the clock')
    sitting = SCR.PACER
    eq(len(sitting.picks), 3, 'three legs')
    eq([round(a) for a in sitting.allocs], [180, 180, 540],
       'shares split by track weight')

    header = ''.join(r.plain() for r in leg1.render(caps))
    ok('left' in header, 'the remaining budget is on screen while you play')
    ok('leg 1/3' in header,
       'and which leg of the sitting you are on, so a first-timer dropped '
       'into an ordinary screen knows they are being timed')
    footer = header
    ok('abandon' in footer,
       'and the footer advertises the key that walks away (contract rule 4)')

    # Leg 1, played correctly, well inside its share.
    clock.advance(100.0)
    lead = next(i for i, l in enumerate(leg1.lines) if l.kind == 'lead')
    for _ in range(lead):
        leg1.handle(K.parse('Down'))
    leg1.handle(K.parse('SPC'))
    nxt = leg1.handle(K.parse('RET')).screen
    if type(nxt).__name__ == 'ActScreen':
        correct = next(i for i, a in enumerate(nxt.body_data.actions)
                       if a.correct)
        for _ in range(correct):
            nxt.handle(K.parse('Down'))
        nxt = nxt.handle(K.parse('RET')).screen
    ok(isinstance(nxt, BetweenScreen), 'a finished leg goes to the between screen')
    ok(bool(nxt.render(caps)), 'which renders')
    eq(len(session.state.attempts), 1,
       'and the leg was recorded as an attempt of its own')
    first = session.state.attempts[0]
    eq(first.sitting, sc.id, 'tagged with the sitting it was played inside')
    eq(first.track, sitting.picks[0].track, 'against its own track')
    eq(first.elapsed, 100.0, 'with the time the sitting clock says it took')
    ok(not first.abandoned, 'and not marked as walked away from')
    ok(first.total > 0, 'a leg played correctly scores')
    ok(len(first.marked) >= 1,
       'the marks are recovered through the on_done seam and stored')

    # Leg 2, abandoned early with the key rather than by calling the method.
    leg2 = nxt.handle(K.parse('RET')).screen
    eq(type(leg2).__name__, 'MarkScreen', 'the between screen opens the next leg')
    ok(SCR.PACER.owns(leg2), 'the pacer owns the leg being played')
    clock.advance(30.0)
    after = leg2.handle(K.parse('X'))
    ok(isinstance(after.screen, BetweenScreen), 'X walks away and moves on')
    eq(len(session.state.attempts), 2, 'and the walk-away is recorded')
    second = session.state.attempts[1]
    ok(second.abandoned, 'marked as abandoned')
    eq(second.total, 0.0, 'scoring nothing')
    eq(second.elapsed, 30.0, 'and costing only the time it took to decide')

    # Leg 3 runs long enough to push the sitting past its budget.
    leg3 = after.screen.handle(K.parse('RET')).screen
    eq(type(leg3).__name__, 'SalvageScreen', 'the last leg is the salvage one')
    clock.advance(800.0)
    ok('budget gone' in SCR.PACER.banner(),
       'the header says so once the budget is spent')
    result = leg3.handle(K.parse('X')).screen
    ok(isinstance(result, SittingResultScreen),
       'the last leg ends the sitting rather than looking for a fourth')
    ok(SCR.PACER is None, 'and the pacer is released')

    r = result.review
    eq(len(r.legs), 3, 'every slot appears in the review')
    eq(r.spent, 930.0, 'spent is the sitting clock')
    eq(r.overspent, 30.0, 'which ran past the budget')
    eq(r.banked, 0.0, 'so nothing was banked')
    eq(r.sunk, 260.0,
       'the late walk-away sank the time it spent past its share, and the '
       'early one sank nothing')
    eq(round(r.score, 1), round(session.state.attempts[0].total / 3, 1),
       'the sitting scores the mean over all three legs')
    ok(not r.passed, 'one leg of three does not clear 60')

    eq(len(session.state.attempts), 4,
       'three legs and the sitting itself are recorded')
    summary = session.state.attempts[-1]
    eq(summary.track, 'proctor', 'the summary row belongs to proctor')
    eq(summary.scenario, sc.id, 'and names the sitting')
    eq(summary.elapsed, 930.0, 'carrying the whole sitting clock')
    ok(0.0 <= summary.precision <= 1.0,
       'precision is the share of the clock that bought something')

    text = ''.join(row.plain() for row in result.render(caps))
    for want in ('sunk', 'unspent', 'What that means'):
        ok(want in text, f'the post-mortem shows {want!r}')
    ok('walked away' in text, 'and names the legs you walked away from')


def test_pacer_release() -> None:
    """Every route out of a sitting puts the clock down.

    A pacer left set paints a dead clock onto the home screen and offers an
    abandon key with nothing to abandon. There are four ways out and all four
    are checked, because the one that gets missed is always the one nobody
    thought of.
    """
    import crux.screens as SCR
    from crux.screens.proctor import SittingIntroScreen

    def open_sitting():
        session = Session.open(clock=FakeClock(), read_only=True)
        sc = session.registry.by_id('proctor-short')
        return SittingIntroScreen(session, sc).handle(K.parse('RET')).screen

    for key, what in (('H', 'home'), ('q', 'quit'), ('ESC', 'back')):
        leg = open_sitting()
        ok(SCR.PACER is not None, f'a sitting is running before {what}')
        leg.handle(K.parse(key))
        ok(SCR.PACER is None, f'{what} releases the pacer')

    # Esc out of a screen the sitting does not own leaves it running: help is
    # not a leg, and closing help should not end the exam.
    leg = open_sitting()
    help_screen = HelpScreen('proctor')
    ok(not SCR.PACER.owns(help_screen), 'the pacer does not own a help page')
    help_screen.handle(K.parse('ESC'))
    ok(SCR.PACER is not None, 'so Esc out of help does not end the sitting')
    caps = all_caps()[0]
    shown = ''.join(r.plain() for r in help_screen.render(caps))
    ok('abandon' not in shown,
       'and a screen the pacer does not own never offers the abandon key')
    ok('left' in shown, 'though the clock is still shown, because it is still '
                        'running')
    leg.handle(K.parse('q'))
    ok(SCR.PACER is None, 'cleaned up')


def test_pacing_screen() -> None:
    """The standalone review renders empty and populated."""
    from crux.screens.proctor import PacingScreen

    caps = all_caps()[0]
    session = Session.open(clock=FakeClock(), read_only=True)
    session.state = State()
    empty = PacingScreen(session)
    text = ''.join(r.plain() for r in empty.render(caps))
    ok('Nothing recorded yet' in text, 'an empty history says so')
    ok(bool(empty.hints(caps)), 'and still names its exits')

    session.state.record(Attempt('sift-a', 'sift', when=1.0, elapsed=200.0,
                                 total=0.0, marks=0.0, recall=0.0,
                                 precision=0.0, tier='graded'))
    session.state.record(Attempt('salvage-a', 'salvage', when=2.0,
                                 elapsed=400.0, total=100.0, marks=100.0,
                                 recall=1.0, precision=1.0, tier='verified',
                                 runs=2, read_first=False))
    full = PacingScreen(session)
    text = ''.join(r.plain() for r in full.render(caps))
    for want in ('on task', 'median', 'zeros', 'What that means'):
        ok(want in text, f'the review shows {want!r}')
    ok('without opening it' in text,
       'and names the read-it-before-you-run-it count when there is one')

    # Every rung of the capability ladder, since this screen is a table.
    for c in all_caps():
        for row in full.render(c):
            ok(R.text_width(row.plain()) <= c.cols,
               'the pacing table never overflows its frame')


# --------------------------------------------------------------------------
# lineage
# --------------------------------------------------------------------------

def _probe_graph():
    """A hand-built domain small enough to reason about in the assertions.

    Two routes to the same account: three edges through a password reset, or
    four through a workstation. The cheap one is the long one, which is the
    whole claim the track makes.
    """
    from crux.targets._graph import Domain, Node, Right
    return Domain(
        nodes=(Node('you', 'user'),
               Node('desk', 'group', name='HELPDESK'),
               Node('it', 'group', name='IT'),
               Node('wk', 'computer'),
               Node('adm', 'user'),
               Node('da', 'group', name='DOMAIN ADMINS'),
               Node('dead', 'computer')),
        edges=(Right('you', 'desk', 'MemberOf'),
               Right('you', 'it', 'MemberOf'),
               Right('desk', 'adm', 'ForceChangePassword', why='loud'),
               Right('it', 'wk', 'AdminTo', why='quiet'),
               Right('wk', 'adm', 'HasSession', why='quiet'),
               Right('adm', 'da', 'MemberOf'),
               Right('it', 'dead', 'CanRDP', why='nothing there')),
        owned=('you',), objective='da', filler=(0, 0))


def test_lineage_arithmetic() -> None:
    """Costs, closure and the two searches, with no screen in the way."""
    built = _probe_graph().build(0)

    have = LN.closure(built.owned, built.edges)
    eq(have, frozenset({'you', 'desk', 'it'}),
       'owning an account owns every group it nests into, free and automatic')
    eq(LN.closure({'adm'}, built.edges), frozenset({'adm', 'da'}),
       'and the closure is transitive rather than one level deep')

    cheap = LN.cheapest(built)
    hops = LN.shortest(built)
    eq(cheap.cost, 3, 'the cheapest route costs the workstation and the session')
    eq(cheap.hops, 4, 'and takes four edges to do it')
    eq(hops.hops, 3, 'the fewest-edges route is one edge shorter')
    eq(hops.cost, 4, 'and costs more, which is the entire claim of the track')
    ok(all(e.kind in LN.EDGE_COST for e in built.edges),
       'every right in a built graph has a price')
    eq(LN.cost_of('MemberOf'), 0, 'a membership is a state, not an action')
    ok(LN.cost_of('ForceChangePassword') > LN.cost_of('HasSession'),
       'resetting a real password costs more than stealing a session')

    moves = LN.available(built, built.owned)
    eq([e.kind for e in moves],
       sorted([e.kind for e in moves], key=lambda k: LN.cost_of(k)),
       'moves are offered cheapest first')
    ok(all(e.kind not in LN.FREE for e in moves),
       'a membership is never offered as a move')
    ok(all(e.dst not in LN.closure(built.owned, built.edges) for e in moves),
       'nor is a right into something you already hold')

    eq(LN.budget_for(3), 6, 'the budget is twice the cheapest route')
    eq(LN.budget_for(1), 3, 'with a floor, so a short graph is not brutal')

    # An unreachable objective is answered, not raised.
    from crux.targets._graph import Domain, Node, Right
    stranded = Domain(nodes=(Node('you', 'user'), Node('da', 'group', name='DA')),
                      edges=(), owned=('you',), objective='da',
                      filler=(0, 0)).build(0)
    ok(not LN.cheapest(stranded).reachable,
       'a domain with no route says so rather than raising')


def test_lineage_scoring() -> None:
    """What a walk is worth, and what it is not worth."""
    built = _probe_graph().build(0)
    cheap = LN.cheapest(built)
    budget = LN.budget_for(cheap.cost)

    best = LN.score_walk(built, list(cheap.priced), True, cheap.cost, budget)
    eq(best.total, 100.0, 'the cheapest route scores full marks')
    eq(best.overspend, 0, 'and overspends nothing')
    ok('cheapest route' in best.summary(), 'and says so')

    reset = [e for e in built.edges if e.kind == 'ForceChangePassword']
    pricey = LN.score_walk(built, reset, True, cheap.cost, budget)
    eq(pricey.spent, 4, 'the reset route costs four')
    eq(pricey.total, 75.0,
       'arriving the expensive way still arrives, and scores less')

    stalled = LN.score_walk(built, [], False, cheap.cost, budget)
    eq(stalled.total, 0.0, 'not arriving is worth nothing')
    eq(stalled.left, 3,
       'and how close you got is reported instead of folded into the score, '
       'the same way a salvage script that meets three of four conditions is')

    dead = [e for e in built.edges if e.kind == 'CanRDP']
    wasted = LN.score_walk(built, dead + list(cheap.priced), True,
                           cheap.cost, budget)
    eq(len(wasted.dead_ends), 1, 'a branch with nothing leading out is named')
    eq(wasted.dead_ends[0].kind, 'CanRDP', 'and it is the right one')
    eq(wasted.spent, 4, 'and it was paid for')
    ok(wasted.total < 100.0, 'so the walk scores less than the clean one')


def test_lineage_content() -> None:
    """Every authored collection: solvable, stable, and teaching its claim."""
    from crux.model import LineageBody

    session = Session.open(clock=FakeClock(), read_only=True)
    scenarios = session.registry.track('lineage').scenarios
    ok(bool(scenarios), 'the lineage track has content')

    for sc in scenarios:
        ok(isinstance(sc.body, LineageBody), f'{sc.id}: carries a LineageBody')
        eq(sc.tier, 'graded', f'{sc.id}: graded, because crux computes the key')

        keys = set()
        for seed in (0, 1, 7, 991, 20260824):
            built = sc.body.build(seed)
            best = LN.cheapest(built)
            ok(best.reachable, f'{sc.id}: reachable at seed {seed}')
            ok(best.cost > 0, f'{sc.id}: not free at seed {seed}')
            ok(built.objective not in LN.closure(built.owned, built.edges),
               f'{sc.id}: you do not start holding it at seed {seed}')
            keys.add(tuple(sorted(e.id for e in best.edges)))
            names = {n.name for n in built.nodes}
            eq(len(names), len(built.nodes),
               f'{sc.id}: no two principals share a display name at seed {seed}')
        eq(len(keys), 1,
           f'{sc.id}: the cheapest route is the same rights at every seed')

        built = sc.body.canonical()
        best = LN.cheapest(built)
        if sc.body.teaches == 'cost':
            ok(LN.shortest(built).cost > best.cost,
               f'{sc.id}: claims to teach cost, so the short route must cost '
               f'more')
        elif sc.body.teaches == 'nesting':
            extra = len(LN.closure(built.owned, built.edges)) - len(built.owned)
            ok(extra >= 2,
               f'{sc.id}: claims to teach nesting, so you must start holding '
               f'more than you were handed')
        elif sc.body.teaches == 'quiet':
            ok(not any(LN.writes(e.kind) for e in best.edges),
               f'{sc.id}: claims to teach quiet, so the cheapest route must '
               f'write nothing to the directory')
            loud = [LN.cheapest_through(built, e) for e in built.edges
                    if LN.writes(e.kind)]
            loud = [r for r in loud if r.reachable]
            ok(bool(loud) and min(r.cost for r in loud)
               <= LN.budget_for(best.cost),
               f'{sc.id}: and an affordable route that writes must also '
               f'arrive, or there is no quieter choice to make')

    # Seeds really do move the surface, or crux D10 is not being honoured.
    sc = scenarios[0]
    a, b = sc.body.build(0), sc.body.build(4242)
    ok(a.domain != b.domain or [n.name for n in a.nodes] != [n.name for n in b.nodes],
       'a different seed produces a different collection to read')


def test_lineage_walk() -> None:
    """Drive the real screen: the cheap route, the expensive one, and giving up."""
    from crux.screens.lineage import MapScreen, WalkResultScreen, WalkScreen

    caps = all_caps()[0]

    def open_walk(scenario='lineage-reset'):
        session = Session.open(clock=FakeClock(), read_only=True)
        session.state = State()
        return session, WalkScreen(session,
                                   session.registry.by_id(scenario), seed=0)

    # The cheapest route, taken deliberately.
    session, walk = open_walk()
    eq(walk.spent, 0, 'a walk starts having spent nothing')
    ok(walk.budget >= walk.best.cost, 'and can afford the cheapest route')
    shown = ''.join(r.plain() for r in walk.render(caps))
    ok('Objective' in shown, 'the objective is named on screen')
    ok('You hold' in shown, 'and so is what you already hold')
    ok('m collection' in shown, 'the footer offers the collection')
    # First contact (empty history) gets the full mechanic spelled out; once
    # a lineage scenario has been finished it collapses to a terse reminder.
    # The collapse is checked on a throwaway session so it does not pollute
    # the attempt history this test asserts on further down.
    ok('New here?' in shown,
       'a player who has never done lineage gets the full explainer')
    seasoned_sess = Session.open(clock=FakeClock(), read_only=True)
    seasoned_sess.state = State()
    seasoned_sess.state.record(Attempt('lineage-reset', 'lineage', when=1.0,
                                       elapsed=60.0, total=100.0, marks=100.0,
                                       recall=1.0, precision=1.0,
                                       tier='graded'))
    seasoned = WalkScreen(seasoned_sess,
                          seasoned_sess.registry.by_id('lineage-culdesac'),
                          seed=0)
    later = ''.join(r.plain() for r in seasoned.render(caps))
    ok('New here?' not in later,
       'and it is gone once the track has been played')

    result = None
    for step in walk.best.priced:
        moves = walk.moves()
        idx = next(i for i, e in enumerate(moves) if e.id == step.id)
        walk.cursor = idx
        action = walk.activate(idx)
        if action.kind == 'replace':
            result = action.screen
    ok(isinstance(result, WalkResultScreen), 'arriving ends the walk')
    eq(result.score.total, 100.0, 'the cheapest route scores full marks')
    ok(result.score.reached, 'and it arrived')
    eq(len(session.state.attempts), 1, 'the attempt was recorded')
    rec = session.state.attempts[0]
    eq(rec.track, 'lineage', 'against the lineage track')
    eq(len(rec.marked), len(walk.best.priced),
       'and the route is stored as the evidence, like a sift marking is')
    eq(rec.precision, 1.0, 'precision is the share of the spend that was needed')
    # `content` rather than `render`: the debrief is longer than a terminal
    # and the frame windows it, so asserting against the painted rows would
    # be asserting about the scroll position rather than about the debrief.
    text = ''.join(r.plain() for r in result.content(caps))
    ok('The cheapest route' in text, 'the debrief shows the cheapest route')
    ok('counts edges' in text,
       'and, on a scenario that teaches it, what a hop-counting map would '
       'have drawn instead')
    ok(result.scrollable(caps),
       'and the debrief is long enough that it has to be scrollable, which is '
       'why the height backstop must never be the thing that trims it')

    # The expensive route: it arrives, and it costs.
    session, walk = open_walk()
    reset = next(i for i, e in enumerate(walk.moves())
                 if e.kind == 'ForceChangePassword'
                 and walk.built.objective
                 in LN.closure({e.dst}, walk.built.edges))
    action = walk.activate(reset)
    ok(action.kind == 'replace', 'the reset arrives in one move')
    score = action.screen.score
    ok(score.reached, 'so it did arrive')
    ok(score.total < 100.0,
       'and scored less, because arriving is not the only thing measured')
    eq(score.spent, LN.cost_of('ForceChangePassword'), 'it cost the reset')

    # Giving up.
    session, walk = open_walk()
    given = walk.handle(K.parse('g')).screen
    eq(given.score.total, 0.0, 'giving up scores nothing')
    ok('gave up' in ''.join(r.plain() for r in given.render(caps)),
       'and the screen says so rather than implying a failure')

    # Running the budget out.
    session, walk = open_walk()
    guard = 0
    ended = None
    while ended is None and guard < 40:
        guard += 1
        moves = walk.moves()
        if not moves:
            break
        # Always the most expensive affordable move, which is how a budget
        # gets burned without arriving.
        idx = max(range(len(moves)),
                  key=lambda i: (LN.cost_of(moves[i].kind)
                                 if LN.cost_of(moves[i].kind) <= walk.left
                                 else -1))
        if LN.cost_of(moves[idx].kind) > walk.left:
            break
        action = walk.activate(idx)
        if action.kind == 'replace':
            ended = action.screen
    ok(ended is not None, 'spending the budget ends the walk one way or another')
    ok(walk.spent <= walk.budget, 'and a walk can never spend past its budget')

    # The collection screen.
    session, walk = open_walk()
    mapped = walk.handle(K.parse('m')).screen
    ok(isinstance(mapped, MapScreen), 'm opens the collection')
    page = ''.join(r.plain() for r in mapped.content(caps))
    for n in walk.built.nodes:
        ok(n.name in page or len(walk.built.nodes) > 20,
           'the collection shows the principals')
        break
    ok('the objective' in page, 'and marks which one is the objective')
    ok(str(len(walk.built.edges)) in page, 'and counts the rights')


def test_lineage_writes_and_waypoints() -> None:
    """The write/read partition, and the through-a-node search behind it."""
    from crux.targets._graph import Domain, Node, Right

    ok(LN.writes('ForceChangePassword'), 'a password reset writes')
    ok(LN.writes('AddMember'), 'adding a member writes')
    ok(not LN.writes('ReadLAPSPassword'), 'reading a LAPS password does not')
    ok(not LN.writes('HasSession'), 'stealing a session writes nothing to AD')
    ok(not LN.writes('AdminTo'), 'nor does connecting to a host')
    ok(all(k in LN.EDGE_COST for k in LN.WRITES),
       'every writing kind is a priced kind')

    # A diamond: one quiet arm and one loud arm reconverge on a shared tail.
    # Deleting the quiet arm's edges would have taken the shared tail with it,
    # which is the bug cheapest_through exists to avoid.
    g = Domain(
        nodes=(Node('you', 'user'), Node('quiet', 'computer'),
               Node('loud', 'user'), Node('mid', 'user'),
               Node('grp', 'group', name='G'), Node('goal', 'computer')),
        edges=(Right('you', 'quiet', 'ReadLAPSPassword', why='q'),
               Right('quiet', 'mid', 'HasSession', why='q'),
               Right('you', 'loud', 'ForceChangePassword', why='l'),
               Right('loud', 'mid', 'HasSession', why='l'),
               Right('mid', 'grp', 'MemberOf'),
               Right('grp', 'goal', 'AdminTo', why='shared tail')),
        owned=('you',), objective='goal', filler=(0, 0)).build(0)

    best = LN.cheapest(g)
    ok(not any(LN.writes(e.kind) for e in best.edges),
       'the cheapest route through the diamond is the quiet arm')

    reset = next(e for e in g.edges if e.kind == 'ForceChangePassword')
    loud = LN.cheapest_through(g, reset)
    ok(loud.reachable, 'a route forced through the loud arm still arrives')
    ok(any(e.kind == 'AdminTo' for e in loud.edges),
       'and it keeps the shared tail the naive deletion would have removed')
    ok(any(LN.writes(e.kind) for e in loud.edges),
       'and it does write, so the quiet choice is a real one')

    # A write edge whose source nothing reaches is not an arriving route,
    # and the search says so rather than raising.
    island = Domain(
        nodes=(Node('you', 'user'), Node('goal', 'computer'),
               Node('lonely', 'user'), Node('off', 'group', name='OFF')),
        edges=(Right('you', 'goal', 'AdminTo', why='direct'),
               Right('lonely', 'off', 'AddMember', why='unreachable')),
        owned=('you',), objective='goal', filler=(0, 0)).build(0)
    orphan = next(e for e in island.edges if e.kind == 'AddMember')
    ok(not LN.cheapest_through(island, orphan).reachable,
       'a write edge whose source you cannot reach is not an arriving route')


def test_sitting_runs_a_lineage_leg() -> None:
    """A sitting can schedule and score a lineage walk, not only the three
    tracks it shipped with.

    The regression this guards is narrow and real: proctor's score reader was
    written `total if sift else total_score`, and a lineage `WalkScore` has
    `total` but no `total_score`, so a lineage leg would have crashed the
    sitting the first time one was drawn. The standard sitting now carries a
    lineage slot, so this also proves that slot fills and plays end to end.
    """
    import crux.screens as SCR
    from crux.screens.proctor import SittingIntroScreen

    clock = FakeClock()
    session = Session.open(clock=clock, read_only=True)
    sc = session.registry.by_id('proctor-standard')
    tracks = [sl.track for sl in sc.body.slots]
    ok('lineage' in tracks, 'the standard sitting has a lineage leg')

    leg = SittingIntroScreen(session, sc).handle(K.parse('RET')).screen
    sitting = SCR.PACER
    ok(sitting is not None, 'the clock is running')

    # Walk each leg to a finish however its engine wants, so the lineage leg
    # in the middle is exercised by the real controller rather than in
    # isolation. Every engine ends a leg by returning a replace() action.
    from crux.screens.lineage import WalkScreen
    from crux.screens.mark import MarkScreen, ActScreen
    from crux.screens.proctor import BetweenScreen, SittingResultScreen

    seen_lineage = False
    guard = 0
    while guard < 20:
        guard += 1
        cur = sitting.current
        clock.advance(30.0)
        if isinstance(cur, WalkScreen):
            seen_lineage = True
            # Take the real cheapest route, so the leg scores rather than
            # merely terminating.
            action = None
            for step in cur.best.priced:
                mv = cur.moves()
                idx = next((j for j, e in enumerate(mv) if e.id == step.id), None)
                if idx is None:
                    continue
                action = cur.activate(idx)
            nxt = action
        elif isinstance(cur, MarkScreen):
            # Abandon is always available and always ends the leg; the point
            # here is the flow, not the sift score.
            nxt = cur.handle(K.parse('X'))
        else:
            nxt = SCR.PACER.abandon()
        scr = nxt.screen
        if isinstance(scr, SittingResultScreen):
            break
        if isinstance(scr, BetweenScreen):
            scr.handle(K.parse('RET'))
        # ActScreen would appear only if a sift leg was played rather than
        # abandoned; the abandon above avoids it.

    ok(seen_lineage, 'the lineage leg was actually reached and played')
    ok(SCR.PACER is None, 'and the sitting cleaned up its pacer')
    lineage_rows = [a for a in session.state.attempts if a.track == 'lineage']
    ok(bool(lineage_rows), 'the lineage leg was recorded as a lineage attempt')
    ok(lineage_rows[0].sitting == sc.id,
       'tagged with the sitting it was played inside')
    ok(lineage_rows[0].total > 0,
       'and the cheapest route scored, proving the score reader handles a '
       'WalkScore')


def test_chain_four_stage_engagement() -> None:
    """Drive chain-aldwych end to end, through the lineage capstone.

    This is the payoff of the chain contract widening: a four-stage engagement
    that finishes on a graph walk rather than a pivot. It proves the lineage
    stage is built by the same seam as the other three, scored by the
    generalised readers, and recorded as one engagement.
    """
    from crux.screens.chain import (BridgeScreen, ChainIntroScreen,
                                    ChainResultScreen)
    from crux.screens.lineage import WalkScreen

    session = Session.open(clock=FakeClock(), read_only=True)
    sc = session.registry.by_id('chain-aldwych')
    eq(tuple(st.track for st in sc.body.stages),
       ('sift', 'salvage', 'conduit', 'lineage'),
       'the engagement is the four-stage AD shape')
    caps = all_caps()[0]

    intro = ChainIntroScreen(session, sc)
    shown = ''.join(r.plain() for r in intro.render(caps))
    ok('take the domain' in shown or 'lineage' in shown,
       'the intro lists the lineage stage')
    ok('4 stages' in shown, 'and counts them correctly, not "Three stages"')
    ok('Three stages' not in shown,
       'the stage count is not hardcoded to three')

    # Stage 1: sift, played clean.
    s1 = intro.handle(K.parse('RET')).screen
    eq(type(s1).__name__, 'MarkScreen', 'begin opens the sift stage')
    lead = next(i for i, l in enumerate(s1.lines) if l.kind == 'lead')
    for _ in range(lead):
        s1.handle(K.parse('Down'))
    s1.handle(K.parse('SPC'))
    act = s1.handle(K.parse('RET')).screen
    correct = next(i for i, a in enumerate(act.body_data.actions) if a.correct)
    for _ in range(correct):
        act.handle(K.parse('Down'))
    b1 = act.handle(K.parse('RET')).screen
    ok(isinstance(b1, BridgeScreen) and b1.stage.track == 'salvage',
       'the sift stage bridges to salvage')

    # Stage 2: salvage, landed.
    s2 = b1.handle(K.parse('RET')).screen
    eq(type(s2).__name__, 'SalvageScreen', 'the bridge opens salvage')
    ok(s2.error == '', 'the salvage target opened inside the chain')
    s2.path.write_text(s2.body_data.render(s2.body_data.solution, s2.url, 0))
    b2 = s2.handle(K.parse('r')).screen
    ok(isinstance(b2, BridgeScreen) and b2.stage.track == 'conduit',
       'landing the exploit bridges to conduit')

    # Stage 3: conduit, or skipped where namespaces are unavailable.
    s3 = b2.handle(K.parse('RET')).screen
    eq(type(s3).__name__, 'ConduitScreen', 'the bridge opens conduit')
    if s3.usable:
        s3.path.write_text(s3.body_data.render(s3.body_data.solution,
                                              str(s3.assets)))
        b3 = s3.handle(K.parse('r')).screen
    else:
        b3 = s3.handle(K.parse('RET')).screen
    ok(isinstance(b3, BridgeScreen) and b3.stage.track == 'lineage',
       'the conduit stage bridges to the lineage capstone, whether it landed '
       'or was skipped')
    low = b3.stage.bridge.lower()
    ok('costs least' in low or 'cheapest' in low or 'fewest edges' in low,
       'and the bridge sets up the cost lesson')

    # Stage 4: lineage, the cheapest route to Domain Admins.
    s4 = b3.handle(K.parse('RET')).screen
    ok(isinstance(s4, WalkScreen), 'the bridge opens the lineage walk')
    eq(s4.scenario.tier, 'graded', 'a lineage stage is graded, like sift')
    # The engagement named the domain aldwych.local in its earlier stages, so
    # the graph must not draw a different one per seed: a chain that called the
    # same box two names would read as two boxes. Checked across seeds because
    # the drawn-domain bug only showed at seeds other than the pinned display.
    for probe in (0, 7, 991):
        built = s4.body_data.build(probe)
        eq(built.domain, 'aldwych.local',
           f'the lineage stage domain stays aldwych.local at seed {probe}')
        ok(built.label(built.objective),
           'and the graph still builds at that seed')
    result = None
    for step in s4.best.priced:
        mv = s4.moves()
        idx = next((j for j, e in enumerate(mv) if e.id == step.id), None)
        if idx is None:
            continue
        action = s4.activate(idx)
        if action.kind == 'replace':
            result = action.screen
    ok(isinstance(result, ChainResultScreen),
       'taking the cheapest route ends the engagement')

    text = ''.join(r.plain() for r in result.content(caps))
    ok('lineage' in text, 'the engagement result lists the lineage stage')
    ok(f'{len(sc.body.stages)}' in result.status
       or 'rooted' in text or 'of 4' in text,
       'and scores over four stages')

    chain_rows = [a for a in session.state.attempts if a.track == 'chain']
    eq(len(chain_rows), 1, 'one engagement attempt recorded')
    eq(chain_rows[0].scenario, 'chain-aldwych', 'under the aldwych id')
    if s3.usable:
        eq(result.chain.passed, 4, 'a clean run passes all four stages')
        eq(chain_rows[0].total, 100.0, 'and scores 100')
    else:
        ok(result.chain.passed >= 3,
           'the sift, salvage and lineage stages pass even when conduit is '
           'skipped for want of namespaces')


def main() -> int:
    for fn in (test_keys, test_render_primitives, test_scoring, test_clock,
               test_state, test_model_guards, test_loader, test_fixtures,
               test_scoring_over_real_content, test_every_scenario_renders,
               test_mock_targets, test_salvage_content, test_salvage_screen,
               test_length_framing, test_hostile_capstone,
               test_result_screens_scroll, test_conduit_engine,
               test_conduit_end_to_end, test_all_conduit_solutions,
               test_chain_flow, test_chain_partial,
               test_chain_four_stage_engagement,
               test_home_shows_composites,
               test_pacing_arithmetic, test_pacing_history, test_sitting_fill,
               test_sitting_flow, test_pacer_release, test_pacing_screen,
               test_lineage_arithmetic, test_lineage_scoring,
               test_lineage_content, test_lineage_walk,
               test_lineage_writes_and_waypoints,
               test_sitting_runs_a_lineage_leg,
               test_list_windowing, test_progress_reset_and_work_files,
               test_result_explains_every_key_line,
               test_no_third_party_attribution,
               test_splash,
               test_screens_render, test_screen_contract, test_walkthrough,
               test_stub_records_nothing, test_session_persists, test_panning):
        fn()
    if FAILURES:
        for f in FAILURES:
            print(f'  FAIL  {f}')
        print(f'{len(FAILURES)} failure(s) in {CHECKS} checks')
        return 1
    print(f'green: {CHECKS} checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
