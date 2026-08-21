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
from crux.config import MIN_COLS, MIN_ROWS, TRACKS            # noqa: E402
from crux.loader import load                                  # noqa: E402
from crux.model import (ConduitBody, ContentError, Line,  # noqa: E402
                        MarkBody, SalvageBody, Scenario, roles)
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
    eq(sorted(reg.tracks), sorted(TRACKS), 'all tracks present')
    ok(len(reg.scenarios) >= 3, 'at least one scenario per track')
    ok(reg.by_id('sift-nmap-pinned') is not None, 'lookup by id')
    ok(reg.by_id('nope') is None, 'unknown id returns None')
    ok(reg.track('sift').ready, 'sift has a real engine')
    ok(reg.track('salvage').ready, 'salvage has a real engine now')
    ok(reg.track('conduit').ready, 'conduit has a real engine now')
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
        ErrorScreen(session),
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


def main() -> int:
    for fn in (test_keys, test_render_primitives, test_scoring, test_clock,
               test_state, test_model_guards, test_loader, test_fixtures,
               test_scoring_over_real_content, test_every_scenario_renders,
               test_mock_targets, test_salvage_content, test_salvage_screen,
               test_length_framing, test_hostile_capstone,
               test_result_screens_scroll, test_conduit_engine,
               test_conduit_end_to_end, test_all_conduit_solutions,
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
