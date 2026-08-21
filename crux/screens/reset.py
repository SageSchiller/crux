"""Erasing progress from inside the app.

Destructive and not undoable, so the screen is built to be hard to trigger by
accident and impossible to trigger without knowing what goes. It states what
is on disk before offering anything, every option needs a second, different
keypress to confirm, and it points at `--export` first, because history that
took weeks to accumulate should not be thrown away by somebody who did not
know they could keep a copy.

Three options rather than one, because "reset" means two different things
depending on what you are stuck on: a history you want to start scoring again
from scratch, or an exercise script you have mangled past saving.
"""

from __future__ import annotations

from .. import progress
from ..config import state_path
from ..render import Caps, Text, line, wrap_rich
from ..session import Session
from . import STAY, Screen

_OPTIONS = (
    ('h', 'history', 'Erase every recorded attempt, score and time.'),
    ('w', 'work', 'Put every exercise script back to its original, and drop '
                  'the generated SSH keypair.'),
    ('a', 'all', 'Both of the above: crux as it was on first run.'),
)


class ResetScreen(Screen):
    def __init__(self, session: Session) -> None:
        self.session = session
        #: Which option is awaiting its confirming keypress, if any.
        self.pending: str | None = None
        self.done: str = ''

    title = 'Reset progress'

    @property
    def status(self) -> str:
        return 'cannot be undone'

    def _summary(self) -> progress.Summary:
        return progress.summary(self.session.state)

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        s = self._summary()
        rows: list[Text] = []

        if self.done:
            rows.append(line(f'  {self.done}', p.ok, bold=True))
            rows.append(Text())
            rows.append(line('  Press esc to go back.', p.dim))
            return rows

        rows.append(line('  On disk right now', p.accent, bold=True))
        rows.append(line(f'    history   {s.history_line()}', p.fg))
        rows.append(line(f'    work      {s.work_line()}', p.fg))
        rows.append(Text())

        if not s.anything:
            rows.append(line('  There is nothing to erase.', p.muted))
            return rows

        if s.attempts:
            rows.extend(wrap_rich(
                caps, 'Keep a copy first if you want one: quit and run '
                      '`crux --export history.json`.',
                caps.cols - 6, '  ', p.muted, p.accent))
            rows.append(Text())

        for key, name, blurb in _OPTIONS:
            selected = self.pending == name
            t = Text().add('  ')
            t.add(key, p.accent2 if selected else p.accent, bold=True)
            t.add(f'  {name}', p.fg, bold=selected)
            rows.append(t)
            rows.extend(wrap_rich(caps, blurb, caps.cols - 10, '       ',
                                  p.muted, p.accent))

        rows.append(Text())
        if self.pending:
            rows.append(line(f'  Press {self.pending[0]} again to erase '
                             f'{self.pending}. This cannot be undone.',
                             p.err, bold=True))
        else:
            rows.append(line('  Pick one. Nothing happens until you press it '
                             'twice.', p.dim))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        if self.pending:
            return [(self.pending[0], f'again to erase {self.pending}'),
                    ('esc', 'cancel'), ('q', 'quit')]
        return [('h', 'history'), ('w', 'work'), ('a', 'all'),
                ('esc', 'back'), ('q', 'quit'), ('?', 'help')]

    def _erase(self, what: str) -> None:
        done = []
        if what in ('history', 'all'):
            progress.clear_history()
            self.session.state.attempts.clear()
            done.append('history')
        if what in ('work', 'all'):
            progress.clear_work()
            done.append('exercise files')
        self.done = 'Erased ' + ' and '.join(done) + '.'

    def handle(self, key):
        name = key.name
        if self.done:
            return super().handle(key)
        if self.pending:
            if name == self.pending[0]:
                self._erase(self.pending)
                self.pending = None
                return STAY
            if name == 'ESC':
                self.pending = None
                return STAY
            return super().handle(key)
        for k, opt, _ in _OPTIONS:
            if name == k and not key.ctrl:
                if self._summary().anything:
                    self.pending = opt
                return STAY
        return super().handle(key)
