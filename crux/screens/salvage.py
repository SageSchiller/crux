"""The salvage screen: a broken exploit, a live target, and your own editor.

**Why the work happens outside crux.** The skill being trained is repairing
somebody else's script, and that is done in the editor you actually use, with
the shell you actually use, against a target that actually answers. A built-in
editor would be a worse version of the one you have and would quietly change
the exercise into something about crux. So the screen hands the terminal back,
gets out of the way, and takes it again afterwards, which is the same handover
`git` uses for `$EDITOR`.

**What crux still does is the part that cannot be faked**: it is the target.
It knows what a correct request looks like because it wrote the service, so it
can say not just that the exploit failed but which condition it failed on, and
it can say the exploit landed without taking your word for it (crux D6).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..clock import Stopwatch, fmt
from ..config import data_dir
from ..model import SalvageBody, Scenario
from ..render import Caps, Text, line, wrap_rich
from ..scoring import score_run
from ..session import Session
from . import STAY, Screen, replace


def _editor() -> list[str]:
    """`$VISUAL`, `$EDITOR`, then whatever is actually installed."""
    for var in ('VISUAL', 'EDITOR'):
        val = os.environ.get(var)
        if val:
            return val.split()
    for cand in ('nvim', 'vim', 'nano', 'vi'):
        found = shutil.which(cand)
        if found:
            return [found]
    return []


class SalvageScreen(Screen):
    def __init__(self, session: Session, scenario: Scenario,
                 on_done=None) -> None:
        self.session = session
        self.scenario = scenario
        self.on_done = on_done
        self.body_data: SalvageBody = scenario.body
        self.watch = Stopwatch(session.clock)
        self.watch.start()

        self.target = None
        #: The trap sink of crux D19, when the scenario has one. A second
        #: loopback service the script must never talk to, so that "you ran a
        #: stranger script without reading it" is something crux can observe
        #: rather than something it can only warn about.
        self.sink = None
        self.path: Path | None = None
        self.runs = 0
        self.opened = False
        #: None until the first run. False means the file was executed without
        #: ever having been opened, which is the whole subject of the crux D19
        #: capstone in Phase 4 and is recorded from now so it is there when
        #: that lands.
        self.read_first: bool | None = None
        self.last: str = ''
        self.error: str = ''
        self._open_target()

    # -- lifecycle ---------------------------------------------------------

    def _open_target(self) -> None:
        from ..targets.mockhttp import MockHttp
        from ..targets.mocktcp import MockTcp
        b = self.body_data
        try:
            if b.kind == 'tcp':
                self.target = MockTcp(b.requirements, banner=b.banner)
            else:
                self.target = MockHttp(b.requirements, route=b.route,
                                       reject_code=b.reject_code,
                                       reject_message=b.reject_message)
            port = self.target.start()
            if b.trap:
                self.sink = MockHttp(b.trap, route='/')
                self.sink.start()
        except OSError as e:
            self.error = f'could not open a target socket: {e}'
            return

        work = data_dir() / 'work' / self.scenario.id
        try:
            work.mkdir(parents=True, exist_ok=True)
            self.path = work / b.filename
            sink_url = self.sink.url if self.sink is not None else ''
            self.path.write_text(b.render(b.broken, self.url, port, sink_url),
                                 encoding='utf-8')
        except OSError as e:
            self.error = f'could not write the exploit file: {e}'

    @property
    def url(self) -> str:
        if self.target is None:
            return ''
        return getattr(self.target, 'url', f'127.0.0.1:{self.target.port}')

    @property
    def tripped(self) -> bool:
        """True once anything at all has reached the trap sink."""
        return self.sink is not None and self.sink.record.count > 0

    def close(self) -> None:
        self.watch.pause()
        for name in ('target', 'sink'):
            svc = getattr(self, name)
            if svc is not None:
                svc.stop()
                setattr(self, name, None)

    # -- handover ----------------------------------------------------------

    def _handover(self, argv: list[str], pause: bool) -> None:
        """Give the terminal back, run something real, take it back.

        The watch stops for the duration. Time spent in your editor is time on
        task and should count; time spent reading a traceback is too. What
        must not count is the terminal being suspended while crux is not the
        thing in front of you, so this pauses only around the subprocess and
        resumes immediately after.
        """
        tty = self.session.terminal

        def go() -> None:
            try:
                # With no terminal there is nobody watching the output, and
                # letting it through writes the exploit script stdout into
                # whatever is running crux headlessly.
                subprocess.run(argv, cwd=str(self.path.parent), check=False,
                               capture_output=tty is None)
            except (OSError, ValueError) as e:
                self.error = f'{argv[0]}: {e}'
                return
            if pause and tty is not None:
                # Only when there was a handover. The pause exists so the
                # script output can be read before crux repaints over it;
                # with no terminal to give back there is nothing to repaint,
                # and `input()` on a stdin nobody is typing into hangs
                # forever, which is exactly what it did to `test.py`.
                try:
                    input('\n[crux] press Enter to return ')
                except (EOFError, KeyboardInterrupt):
                    pass

        if tty is None:
            go()
        else:
            with tty.suspended():
                go()

    def _edit(self):
        argv = _editor()
        if not argv or self.path is None:
            self.error = 'no editor found: set $EDITOR'
            return STAY
        self.opened = True
        self._handover(argv + [str(self.path)], pause=False)
        return STAY

    def _run(self):
        if self.path is None or self.target is None:
            return STAY
        if self.read_first is None:
            self.read_first = self.opened
        self.runs += 1
        self._handover([sys.executable, str(self.path)], pause=True)
        landed, detail, met = self.target.verdict()
        self.last = detail
        # Tripping the trap ends the scenario immediately whether or not the
        # exploit worked. That is the lesson: on a real engagement the damage
        # is done at the moment you press enter, and how well the rest of the
        # script performed afterwards is not the interesting question.
        if landed or self.tripped:
            return self._finish()
        return STAY

    def _finish(self):
        landed, detail, met = self.target.verdict()
        if self.tripped:
            landed = False
            detail = 'the script contacted an address of its own before it '\
                     'did anything you asked it to'
        score = score_run(landed, met, len(self.body_data.requirements),
                          detail, self.runs, self.read_first,
                          self.watch.elapsed())
        if self.on_done is not None:
            return self.on_done(score)
        self.session.record_run(self.scenario, score)
        from .runresult import RunResultScreen
        return replace(RunResultScreen(self.session, self.scenario, score,
                                       self.target.record, self.tripped,
                                       self.sink))

    # -- view --------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.scenario.title

    @property
    def status(self) -> str:
        if self.error:
            return 'unavailable'
        return f'{self.runs} run{"" if self.runs == 1 else "s"}'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        b = self.body_data
        if self.error:
            return [line(f'  {self.error}', p.err), Text(),
                    line('  Nothing is scored on this screen.', p.dim)]

        rows = wrap_rich(caps, b.brief, caps.cols - 6, '  ', p.fg, p.accent)
        rows.append(Text())
        rows.append(line(f'  target   {self.url}', p.info))
        rows.append(line(f'  file     {self.path}', p.info))
        rows.append(Text())

        n = self.target.record.count if self.target else 0
        t = Text().add('  requests received  ', p.muted).add(str(n), p.fg)
        t.add('     time  ', p.muted).add(fmt(self.watch.elapsed()), p.fg)
        rows.append(t)

        if self.tripped:
            rows.append(line('  the script contacted an address of its own',
                             p.err, bold=True))
        if self.runs:
            _, detail, met = self.target.verdict()
            total = len(b.requirements)
            bar = Text().add('  conditions met     ', p.muted)
            bar.add(f'{met}/{total}', p.ok if met == total else p.warn,
                    bold=True)
            rows.append(bar)
            rows.append(Text())
            rows.extend(wrap_rich(caps, f'**Closest attempt:** {detail}',
                                  caps.cols - 6, '  ', p.warn, p.accent))
        else:
            rows.append(Text())
            rows.append(line('  Read it before you run it.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [('e', 'edit'), ('r', 'run'), ('g', 'give up'),
                ('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')]

    def handle(self, key):
        if self.error:
            return super().handle(key)
        if key.name == 'e' and not key.ctrl:
            return self._edit()
        if key.name == 'r' and not key.ctrl:
            return self._run()
        if key.name == 'g' and not key.ctrl and self.runs:
            return self._finish()
        return super().handle(key)
