"""Help, because every footer advertises `?` and a key you were shown that does
nothing is the rule-4 failure the footer contract exists to prevent."""

from __future__ import annotations

from ..config import APP_TITLE, TIER_MEANING, TIERS
from ..render import Caps, Text, line, wrap_rich
from . import Screen

_ABOUT = (
    '**crux** drills the judgement parts of an engagement: reading raw output '
    'for the lead (`sift`), repairing a proof-of-concept until it lands '
    '(`salvage`), and building the tunnel that reaches the next subnet '
    '(`conduit`). It never touches anything it did not create.'
)

_SCORING = (
    'In `sift`, marking everything loses. The score is the harmonic mean of '
    'precision and recall, and a decoy costs double a stray mark, so missing a '
    'lead and chasing a rabbit hole cost you the same. Some screens contain '
    'nothing at all, and on those the correct answer is to submit with nothing '
    'marked.'
)


class HelpScreen(Screen):
    title = f'{APP_TITLE}: help'

    def body(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows = wrap_rich(caps, _ABOUT, caps.cols - 6, '  ', p.fg, p.accent)
        rows.append(Text())
        rows.extend(wrap_rich(caps, _SCORING, caps.cols - 6, '  ', p.muted,
                              p.accent))
        rows.append(Text())
        rows.append(line('  Verification tiers', p.accent, bold=True))
        for t in TIERS:
            rows.append(line(f'    {t:<10}{TIER_MEANING[t]}', p.muted))
        rows.append(Text())
        rows.append(line('  Keys', p.accent, bold=True))
        for k, v in (('up/down, j/k', 'move'), ('space', 'mark a line'),
                     ('enter', 'submit, or open'), ('esc', 'back'),
                     ('H', 'home'), ('q', 'quit')):
            rows.append(line(f'    {k:<14}{v}', p.muted))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return [('esc', 'back'), ('q', 'quit')]
