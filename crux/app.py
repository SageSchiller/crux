"""Entry point: argument parsing, the screen stack, and the main loop.

The loop is deliberately dull. It renders the top screen, waits for a key,
hands the key to that screen, and does what the returned action says. Every
interesting decision lives in a screen or in `scoring.py`, which is what keeps
this file from becoming the place where behaviour hides.

**Every exit path closes every stacked screen.** A screen cannot see the `q`
that quits the app from three levels down, and from Phase 3 the things screens
hold are mock services and network namespaces rather than just memory. Leaking
one of those is worse than a wedged terminal, because the next run inherits it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import progress
from . import render as R
from . import splash as SP
from . import term as T
from .clock import RealClock, fmt
from .config import APP_NAME, APP_TITLE, MIN_COLS, MIN_ROWS, SECTIONS, TRACKS
from .loader import load
from .session import Session
from .state import State
from .version import VERSION
from . import screens as S
from .screens.help import HelpScreen
from .screens.home import HomeScreen


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog=APP_NAME, add_help=True,
                                 description='Drills for the judgement parts '
                                             'of an engagement.')
    ap.add_argument('--version', action='store_true', help='print version and exit')
    ap.add_argument('--theme', default=None,
                    help='cyberpunk-neon (default), neutral, or ansi')
    ap.add_argument('--ascii', action='store_true',
                    help='force the ASCII glyph set')
    ap.add_argument('--doctor', action='store_true',
                    help='report what this terminal and machine support')
    ap.add_argument('--export', metavar='PATH',
                    help='write attempt history to PATH and exit')
    ap.add_argument('--import', dest='import_', metavar='PATH',
                    help='merge attempt history from PATH and exit')
    ap.add_argument('--reset', nargs='?', const='all',
                    choices=('history', 'work', 'all'), default=None,
                    metavar='WHAT',
                    help='erase progress and exit: history (recorded '
                         'attempts), work (your edited scripts), or all '
                         '(default). Prints what will go and asks first')
    ap.add_argument('--yes', action='store_true',
                    help='skip the confirmation for --reset')
    ap.add_argument('--seed', type=int, default=None,
                    help='pin every fixture to this seed instead of drawing '
                         'a fresh one per attempt; use it to reproduce an '
                         'attempt from the seed stored in your history')
    ap.add_argument('--no-splash', action='store_true',
                    help='skip the opening and closing animations')
    ap.add_argument('--no-alt-screen', action='store_true',
                    help='do not use the alternate screen buffer')
    return ap.parse_args(argv)


def _doctor() -> int:
    """What this machine supports, said plainly. No scenario is run."""
    import shutil
    caps = R.detect_caps()
    print(f'{APP_TITLE} {VERSION}')
    print(f'  python        {sys.version.split()[0]}')
    print(f'  tty           {T.is_tty()}')
    cols, rows = T.size()
    print(f'  size          {cols}x{rows}'
          f'{"  (below the " + str(MIN_COLS) + "x" + str(MIN_ROWS) + " minimum)" if T.too_small() else ""}')
    print(f'  colour        {caps.color.name}')
    print(f'  glyphs        {caps.glyphs.name}')
    print(f'  kitty keys    {T.kitty_supported()}')
    reg = load()
    for name in SECTIONS:
        tr = reg.track(name)
        print(f'  {name:<9}{len(tr.scenarios)} scenario(s)'
              f'{"" if tr.ready else "   engine not built yet"}')
    for e in reg.errors:
        print(f'  LOAD ERROR    {e}')
    print('  conduit needs unprivileged user namespaces plus:')
    for tool in ('ip', 'unshare', 'nsenter', 'socat', 'ssh', 'sshd',
                 'proxychains4', 'chisel'):
        # sshd is not on a normal PATH, and conduit runs it unprivileged on a
        # high port rather than touching the system service.
        where = shutil.which(tool)
        if where is None and tool == 'sshd':
            where = next((c for c in ('/usr/sbin/sshd', '/usr/bin/sshd')
                          if Path(c).exists()), None)
        print(f'    {tool:<14}{where or "MISSING"}')
    st = State.load()
    print(f'  history       {len(st.attempts)} attempt(s), '
          f'{fmt(st.time_on_task())} on task')
    if st.damaged:
        print(f'  HISTORY       {st.damaged}')
    return 0


def _reset(what: str, assume_yes: bool = False) -> int:
    """Erase progress, after saying exactly what will go.

    Destructive and not undoable, so it states the damage in full and asks,
    unless `--yes`. It also names `--export` on the way past: history that took
    weeks to accumulate should not be thrown away by somebody who did not know
    they could keep a copy.
    """
    s = progress.summary()
    doing_history = what in ('history', 'all')
    doing_work = what in ('work', 'all')

    print(f'{APP_TITLE} reset: {what}')
    if doing_history:
        print(f'  history   {s.history_line()}')
    if doing_work:
        print(f'  work      {s.work_line()}')
    if not s.anything:
        print('\nThere is no progress to erase.')
        return 0
    if doing_history and s.attempts:
        print('\n  Keep a copy first with:  crux --export history.json')

    if not assume_yes:
        try:
            answer = input('\nErase this? It cannot be undone. [y/N] ')
        except (EOFError, KeyboardInterrupt):
            print()
            answer = ''
        if answer.strip().lower() not in ('y', 'yes'):
            print('Nothing was erased.')
            return 1

    done = []
    if doing_history and progress.clear_history():
        done.append('history')
    if doing_work and progress.clear_work():
        done.append('work files')
    print('Erased ' + ' and '.join(done) + '.' if done
          else 'Nothing needed erasing.')
    return 0


def _export(path: str) -> int:
    st = State.load()
    Path(path).write_text(st.export_json(), encoding='utf-8')
    print(f'wrote {len(st.attempts)} attempt(s) to {path}')
    return 0


def _import(path: str) -> int:
    incoming = State.load(Path(path))
    if incoming.damaged:
        print(f'could not import: {incoming.damaged}', file=sys.stderr)
        return 1
    mine = State.load()
    added = mine.merge(incoming)
    mine.save()
    print(f'merged {added} new attempt(s); history now {len(mine.attempts)}')
    return 0


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.version:
        print(f'{APP_NAME} {VERSION}')
        return 0
    if args.doctor:
        return _doctor()
    if args.reset:
        return _reset(args.reset, assume_yes=args.yes)
    if args.export:
        return _export(args.export)
    if args.import_:
        return _import(args.import_)

    if not T.is_tty():
        print(f'{APP_NAME}: needs an interactive terminal. '
              f'Try `{APP_NAME} --doctor`.', file=sys.stderr)
        return 2

    S.set_help_factory(HelpScreen)
    session = Session.open(clock=RealClock(), seed_override=args.seed)
    stack: list[S.Screen] = [HomeScreen(session)]

    with T.managed(use_alt_screen=not args.no_alt_screen) as tty:
        # Screens that hand the terminal back for an editor or a subprocess
        # need the Terminal itself. Held on the session rather than threaded
        # through every constructor, and None outside a TTY so the handover
        # helper can degrade to running in place.
        session.terminal = tty
        # The entrance, and the exit, both honour --no-splash. The intro loads
        # nothing (Session.open already did), so it is pure identity: the name
        # resolving out of noise, which is the app's own thesis as its door.
        splash_caps = R.detect_caps(theme=args.theme, ascii_only=args.ascii,
                                    cols=T.size()[0], rows=T.size()[1])
        show_splash = not args.no_splash and not T.too_small()
        if show_splash:
            SP.play(tty, splash_caps, note=SP.scope_note(session.registry))
        # Repaint in place, and only when the frame actually changed. The old
        # loop erased the whole screen (\x1b[2J) and redrew on every pass,
        # including the twice-a-second idle pass on the read timeout, which
        # read as a flicker while you were just looking at a menu. Home the
        # cursor, overwrite, and clear below instead: an unchanged frame is
        # not rewritten at all, and a changed one is drawn over the last one
        # without a blanking flash.
        last_paint = None
        try:
            while stack:
                cols, rows = T.size()
                caps = R.detect_caps(theme=args.theme, ascii_only=args.ascii,
                                     cols=cols, rows=rows)
                screen = stack[-1]
                if T.too_small():
                    out = _too_small(caps)
                else:
                    out = R.render_lines(caps, screen.render(caps))
                token = (cols, rows, out)
                if token != last_paint:
                    # **CRLF, not LF.** The terminal is in raw mode, so OPOST
                    # is off and a bare newline moves down without returning
                    # the carriage: the next line then starts at the right
                    # edge, wraps, and eats a second physical row. That is why
                    # the menu was drawing on every other row with the frame
                    # underneath showing through between entries, and why so
                    # few items fitted on screen. The splash always converted;
                    # the main loop never did.
                    #
                    # Erase each line to its end before the break and erase
                    # below the last one, so a shorter frame leaves nothing of
                    # a taller one behind. No full-screen erase, so no flash.
                    painted = ('\x1b[H' + out.replace('\n', '\x1b[K\r\n')
                               + '\x1b[K\x1b[J')
                    tty.write(painted)
                    last_paint = token

                keys = tty.read_keys(timeout=0.5)
                if not keys:
                    continue
                for key in keys:
                    action = screen.handle(key)
                    if action.kind == 'stay':
                        continue
                    if action.kind == 'push':
                        stack.append(action.screen)
                    elif action.kind == 'replace':
                        stack.pop().close()
                        stack.append(action.screen)
                    elif action.kind == 'pop':
                        if len(stack) > 1:
                            stack.pop().close()
                    elif action.kind == 'root':
                        while len(stack) > 1:
                            stack.pop().close()
                    elif action.kind == 'quit':
                        while stack:
                            stack.pop().close()
                    break
        finally:
            for s in stack:
                s.close()
            if show_splash:
                cols, rows = T.size()
                SP.outro(tty, R.detect_caps(theme=args.theme,
                                            ascii_only=args.ascii,
                                            cols=cols, rows=rows))
    return 0


def _too_small(caps: R.Caps) -> str:
    """A terminal below the documented minimum still gets a readable message."""
    cols, rows = T.size()
    lines = [
        R.line(f'{APP_TITLE} needs {MIN_COLS}x{MIN_ROWS}.', caps.palette.warn),
        R.line(f'This terminal is {cols}x{rows}.', caps.palette.muted),
        R.line('Resize, or press q to quit.', caps.palette.dim),
    ]
    return R.render_lines(caps, lines)
