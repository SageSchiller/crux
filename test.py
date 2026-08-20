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
from crux.model import ContentError, Line, MarkBody, Scenario, roles  # noqa: E402
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
    ok(not reg.track('salvage').ready, 'salvage is honestly marked unbuilt')
    ok(len(reg.track('sift').scenarios) >= 9, 'sift has real breadth')
    ok(reg.by_id('sift-smoke-nmap') is None,
       'Phase 0 scaffolding was deleted, not left beside real content')


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
    stub = session.registry.by_id('salvage-smoke')
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
    session = Session.open(clock=FakeClock(), read_only=True)
    before = len(session.state.attempts)
    from crux.screens.stub import StubScreen
    scr = StubScreen(session, session.registry.by_id('conduit-smoke'))
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
