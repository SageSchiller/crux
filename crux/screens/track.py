"""One track's scenarios.

Each row carries the tier badge, because crux D6 says the three tiers are never
blurred and a list is exactly where blurring happens: `verified` and `self`
render identically unless something on the row says otherwise.
"""

from __future__ import annotations

from ..model import ConduitBody, SalvageBody, StubBody, missing_needs
from ..render import Caps, Text, line, wrap_rich
from ..session import Session
from . import ListScreen, Screen, push, selector

TIER_MARK = {'verified': 'verified', 'graded': 'graded', 'self': 'self-marked'}


class TrackScreen(ListScreen):
    def __init__(self, session: Session, track_name: str) -> None:
        super().__init__()
        self.session = session
        self.track_name = track_name
        self.track = session.registry.track(track_name)
        self.help_topic = track_name

    @property
    def title(self) -> str:
        return self.track_name

    @property
    def status(self) -> str:
        return self.track.blurb

    def count(self) -> int:
        return len(self.track.scenarios)

    #: One line each: what a scenario in this track asks of you. Shown above
    #: the list so a new player knows the goal before opening anything. `?`
    #: has the full version.
    _INTRO = {
        'sift': 'Each is a screen of real tool output. Mark the lines that '
                'change your next move, then submit.  ? for how.',
        'salvage': 'Each hands you a broken exploit and a live target. Fix it '
                   'in your editor and run it.  ? for how.',
        'conduit': 'Each is a real network you must cross. Edit the tunnel '
                   'script and run it; crux probes the path.  ? for how.',
        'chain': 'One full engagement through all three tracks: find the way '
                 'in, land the exploit, reach the next host.  ? for how.',
    }

    def header_rows(self, caps: Caps) -> list[Text]:
        p = caps.palette
        intro = self._INTRO.get(self.track_name)
        if not intro:
            return []
        rows = wrap_rich(caps, intro, caps.cols - 6, '  ', p.muted, p.accent)
        rows.append(Text())
        return rows

    def empty_state(self, caps: Caps) -> list[Text]:
        return [line('  No scenarios in this track yet.', caps.palette.muted)]

    def blocks(self, caps: Caps) -> list[list[Text]]:
        """One tight row per scenario: a status dot, the title, and the tier
        badge with any best score or missing tool folded in on the right.

        One row rather than two, because the tier is a small thing and a second
        line for it halved how many scenarios were on screen. The status suffix
        is built first so the title can be truncated to leave room for it,
        rather than the title shoving the badge off the edge."""
        p = caps.palette
        out: list[list[Text]] = []
        for i, s in enumerate(self.track.scenarios):
            sel = i == self.cursor
            best = self.session.state.best(s.id)
            if best is None:
                mark, mcol = caps.g('dot_off'), p.dim
            elif best.total >= 90:
                mark, mcol = caps.g('check'), p.ok
            else:
                mark, mcol = caps.g('dot_on'), p.warn

            tier = TIER_MARK.get(s.tier, s.tier)
            tcol = (p.ok if s.tier == 'verified' else
                    p.info if s.tier == 'graded' else p.warn)
            suffix = Text().add('  ')
            miss = missing_needs(s)
            if isinstance(s.body, StubBody):
                suffix.add(f'{s.body.phase}  ', p.warn)
            suffix.add(tier, tcol)
            if miss:
                suffix.add(f'  needs {", ".join(miss)}', p.warn)
            elif best is not None:
                suffix.add(f'  best {best.total:.0f}', p.dim)

            # room for: selector(3) + borders(2) + dot(2) + a gap before suffix
            room = max(8, caps.cols - 3 - 2 - 2 - suffix.width() - 2)
            title = s.title if len(s.title) <= room else s.title[:room - 1] + caps.g('ellipsis')

            t = selector(caps, sel)
            t.add(f'{mark} ', mcol)
            t.add(title, p.accent if sel else p.fg, bold=sel)
            t.pad_to(caps.cols - 2 - suffix.width())
            t.spans.extend(suffix.spans)
            out.append([t])
        return out

    def activate(self, index: int) -> object:
        from .mark import MarkScreen
        from .salvage import SalvageScreen
        from .stub import StubScreen
        s = self.track.scenarios[index]
        from ..model import ChainBody
        if isinstance(s.body, ChainBody):
            from .chain import ChainIntroScreen
            return push(ChainIntroScreen(self.session, s))
        miss = missing_needs(s)
        if miss:
            return push(NeedsScreen(self.session, s, miss))
        if isinstance(s.body, StubBody):
            return push(StubScreen(self.session, s))
        if isinstance(s.body, SalvageBody):
            return push(SalvageScreen(self.session, s))
        if isinstance(s.body, ConduitBody):
            from .conduit import ConduitScreen
            return push(ConduitScreen(self.session, s))
        return push(MarkScreen(self.session, s))


_INSTALL = {
    'chisel': 'https://github.com/jpillora/chisel/releases (single static binary)',
    'ligolo-ng': 'https://github.com/nicocha30/ligolo-ng/releases',
    'socat': 'apt install socat  /  pacman -S socat',
    'proxychains': 'apt install proxychains4  /  pacman -S proxychains-ng',
}


class NeedsScreen(Screen):
    """Shown when a scenario names a tool that is not installed.

    A missing tool is not a failure and this screen scores nothing. It names
    what is missing and where to get it, then gets out of the way, which is
    the same courtesy hone extends to a module whose real tool is absent.
    """

    def __init__(self, session, scenario, missing) -> None:
        self.session = session
        self.scenario = scenario
        self.missing = missing

    @property
    def title(self) -> str:
        return self.scenario.title

    status = 'tool not installed'

    def body(self, caps):
        from ..render import line, wrap_rich
        p = caps.palette
        rows = [line('  This scenario needs a tool you do not have '
                     'installed.', p.warn, bold=True), Text()]
        for tool in self.missing:
            rows.append(line(f'  {tool}', p.fg, bold=True))
            if tool in _INSTALL:
                rows.append(line(f'      {_INSTALL[tool]}', p.dim))
        rows.append(Text())
        rows.append(line('  Nothing here is scored. Install what is missing '
                         'and it becomes playable.', p.dim))
        return rows

    def hints(self, caps):
        return [('esc', 'back'), ('H', 'home'), ('q', 'quit'), ('?', 'help')]
