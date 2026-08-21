"""The conduit screen: a network you cannot reach across.

Same shape as salvage, deliberately. You are handed a file, you edit it in
your own editor, you run it, and crux tells you exactly what did and did not
become reachable. The difference is what is on the other side: instead of a
socket pretending to be a vulnerable service, it is a real multi-hop network
built out of unprivileged namespaces, with a real `sshd` on the pivot.

**Every run rebuilds the whole network and tears it down.** That costs a few
seconds and buys the thing that matters: there is no state to leak between
attempts and no supervisor whose death has to be survivable.

**When the kernel will not allow it, this screen says so and scores nothing**
(crux D14). Unprivileged user namespaces are switched off on some systems and
absent from some kernels, and a track that quietly pretended to verify on
those machines would be worth less than one that admits it cannot.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..clock import Stopwatch, fmt
from ..config import data_dir
from ..model import ConduitBody, Scenario
from ..render import Caps, Text, line, wrap_rich
from ..scoring import score_run
from ..session import Session
from ..targets.netns import capability, prepare_assets, run_attempt
from . import STAY, Screen, replace


def _editor() -> list[str]:
    for var in ('VISUAL', 'EDITOR'):
        val = os.environ.get(var)
        if val:
            return val.split()
    for cand in ('nvim', 'vim', 'nano', 'vi'):
        found = shutil.which(cand)
        if found:
            return [found]
    return []


class ConduitScreen(Screen):
    def __init__(self, session: Session, scenario: Scenario,
                 on_done=None) -> None:
        self.session = session
        self.scenario = scenario
        self.on_done = on_done
        self.body_data: ConduitBody = scenario.body
        self.watch = Stopwatch(session.clock)
        self.watch.start()

        self.runs = 0
        self.opened = False
        self.last = None
        self.error = ''
        self.path: Path | None = None
        self.assets: Path | None = None

        usable, why = capability()
        self.usable = usable
        if not usable:
            self.error = why
            return
        try:
            work = data_dir() / 'work' / scenario.id
            self.assets = prepare_assets(data_dir() / 'work' / '_assets')
            work.mkdir(parents=True, exist_ok=True)
            self.path = work / self.body_data.filename
            if not self.path.exists():
                self.path.write_text(
                    self.body_data.render(self.body_data.starter,
                                          str(self.assets)),
                    encoding='utf-8')
        except (OSError, subprocess.SubprocessError) as e:
            self.error = f'could not prepare the scenario: {e}'

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self.watch.pause()

    # -- handover ----------------------------------------------------------

    def _handover(self, fn, pause: bool):
        tty = self.session.terminal

        def go():
            result = fn()
            if pause and tty is not None:
                try:
                    input('\n[crux] press Enter to return ')
                except (EOFError, KeyboardInterrupt):
                    pass
            return result

        if tty is None:
            return go()
        with tty.suspended():
            return go()

    def _edit(self):
        argv = _editor()
        if not argv or self.path is None:
            self.error = 'no editor found: set $EDITOR'
            return STAY
        self.opened = True
        self._handover(
            lambda: subprocess.run(argv + [str(self.path)], check=False),
            pause=False)
        return STAY

    def _run(self):
        if self.path is None or self.assets is None:
            return STAY
        self.runs += 1

        def go():
            quiet = self.session.terminal is None
            if not quiet:
                print('\n[crux] building the network and running your '
                      'script, this takes a few seconds ...\n', flush=True)
            result = run_attempt(self.body_data.topology, self.path,
                                 self.assets, self.body_data.settle)
            if not quiet:
                if result.script_output.strip():
                    print(result.script_output.rstrip())
                for pr in result.probes:
                    mark = 'reachable  ' if pr['ok'] else 'UNREACHABLE'
                    print(f"[crux] {mark} {pr['name']} from {pr['from']}")
                if result.error:
                    print(f'[crux] {result.error}')
            return result

        self.last = self._handover(go, pause=True)
        if self.last is not None and self.last.ok:
            return self._finish()
        return STAY

    def _finish(self):
        r = self.last
        ok = bool(r and r.ok)
        detail = (r.detail or r.error) if r else 'not run'
        score = score_run(ok, r.met if r else 0, r.total if r else 0, detail,
                          self.runs, None, self.watch.elapsed())
        if self.on_done is not None:
            return self.on_done(score)
        self.session.record_run(self.scenario, score)
        from .conduitresult import ConduitResultScreen
        return replace(ConduitResultScreen(self.session, self.scenario, score,
                                           r))

    # -- view --------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        if not self.usable:
            return 'unavailable here'
        return f'{self.runs} run{"" if self.runs == 1 else "s"}'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        if not self.usable:
            rows = [line('  This track cannot verify anything on this '
                         'machine.', p.warn, bold=True), Text()]
            rows.extend(wrap_rich(
                caps,
                f'conduit builds real networks out of **unprivileged user '
                f'namespaces**, and this kernel will not allow it: `{self.error}`. '
                'Nothing here is scored, because a score crux cannot stand '
                'behind is worth less than none.',
                caps.cols - 6, '  ', p.muted, p.accent))
            return rows
        if self.error:
            return [line(f'  {self.error}', p.err)]

        rows = wrap_rich(caps, self.body_data.brief, caps.cols - 6, '  ',
                         p.fg, p.accent)
        rows.append(Text())
        rows.append(line(f'  script   {self.path}', p.info))
        rows.append(line(f'  key      {self.assets}/id', p.info))
        rows.append(Text())
        t = Text().add('  time  ', p.muted).add(fmt(self.watch.elapsed()), p.fg)
        rows.append(t)

        if self.last is not None:
            rows.append(Text())
            for pr in self.last.probes:
                mark = caps.g('check') if pr['ok'] else caps.g('cross')
                row = Text().add('  ')
                row.add(mark, p.ok if pr['ok'] else p.err)
                row.add(f" {pr['name']}", p.fg)
                row.add(f"   from {pr['from']}", p.dim)
                rows.append(row)
            if self.last.error:
                rows.append(line(f'  {self.last.error}', p.err))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        if not self.usable:
            base = ([('ret', 'skip this leg')] if self.on_done is not None
                    else [])
            return base + [('esc', 'back'), ('H', 'home'), ('q', 'quit'),
                           ('?', 'help')]
        return [('e', 'edit'), ('r', 'build and run'), ('g', 'give up'),
                ('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')]

    def handle(self, key):
        if not self.usable or self.error:
            # In a chain, an unverifiable conduit leg must not be a dead end:
            # let the engagement continue with an honestly-skipped score
            # rather than trapping the student on a screen with no run key.
            if self.on_done is not None and key.name in ('RET', 'g'):
                from ..scoring import score_run
                return self.on_done(score_run(
                    False, 0, 1, 'skipped: namespaces unavailable here', 0,
                    None, self.watch.elapsed()))
            return super().handle(key)
        if key.name == 'e' and not key.ctrl:
            return self._edit()
        if key.name == 'r' and not key.ctrl:
            return self._run()
        if key.name == 'g' and not key.ctrl and self.runs:
            return self._finish()
        return super().handle(key)
