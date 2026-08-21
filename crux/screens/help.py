"""Context help. `?` opens the guidance for the track you are in, because a
key the footer advertises that shows a generic page is barely better than one
that does nothing.

Every screen carries a `help_topic`; the base handler passes it here, and this
renders the "what you are doing, how to play it, how you are scored" for that
track, plus how crux relates to real practice. Someone who opens `?` while
staring at a wall of nmap output should get told what to do with it.
"""

from __future__ import annotations

from ..config import APP_TITLE, TIER_MEANING, TIERS
from ..render import Caps, Text, line, wrap_rich
from . import ScrollScreen

_ABOUT = (
    '**crux** drills the three judgements an engagement actually turns on. '
    '**sift**: read a screen of tool output and find the lead. **salvage**: '
    'take a broken exploit and make it land. **conduit**: pivot from a '
    'foothold to the next host. It never touches anything it did not create.'
)

_REAL = (
    '**Are these real?** The `sift` scenarios are modelled on real attack '
    'chains. The output is the shape the tools actually produce, and the line '
    'that mattered is the line that mattered. `salvage` and `conduit` run '
    'against **synthetic targets on your own loopback**, on purpose: crux '
    'ships no working exploit for real software and is safe to hand to '
    'anyone. Each `salvage` exercise names the real CVE its defect comes '
    'from, among them Drupalgeddon2, Shellshock, EternalBlue, Log4Shell and '
    'the Apache 2.4.49/2.4.50 traversal. The defect you repair is the one '
    'that broke that real proof-of-concept; only the vulnerable service is a '
    'stand-in.'
)

_TOPICS = {
    'sift': (
        'sift: find the lead',
        [
            ('What you are doing',
             'You are looking at a screen of real tool output, the way it '
             'comes back on an engagement. Somewhere in it is the one line '
             '(or two) that changes what you do next. Find it.'),
            ('How to play',
             'Move with the arrows. Press **space** to mark a line, space '
             'again to unmark it. When you have marked what matters, press '
             '**enter** to submit. Then pick what the lead earns you.'),
            ('The catch',
             'Some screens have **no lead at all**, the honest common '
             'case. When that is true, the right answer is to submit with '
             'nothing marked and move on.'),
            ('How you are scored',
             'On precision and recall together. Marking everything loses: a '
             'wrong mark costs you, and a mark on a decoy (a line authored to '
             'tempt) costs double. Missing a real lead and chasing a rabbit '
             'hole cost the same.'),
        ],
    ),
    'salvage': (
        'salvage: make it land',
        [
            ('What you are doing',
             'You are handed a broken proof-of-concept and a live target on '
             'your loopback. The exploit does not work as written. Repair it '
             'and land it.'),
            ('How to play',
             'Press **e** to open the script in your own editor, fix it, save '
             'and quit. Press **r** to run it against the target. crux is the '
             'target, so it tells you exactly which condition your request '
             'still misses. **g** gives up and shows the answer.'),
            ('The habit',
             'Read it before you run it. A script you did not write can do '
             'more than you wanted, and one scenario here will prove it.'),
            ('How you are scored',
             'It landed, or it did not. An exploit that meets three of four '
             'conditions still does not work, so the score is landed / not, '
             'and the checklist shows you how close you were.'),
        ],
    ),
    'conduit': (
        'conduit: reach the next host',
        [
            ('What you are doing',
             'A service on an internal host answers only through a pivot you '
             'have a foothold on. crux builds that network for real out of '
             'unprivileged namespaces. Make the service reachable from your '
             'box.'),
            ('How to play',
             'Press **e** to edit the tunnel script, **r** to build the '
             'network and run it. crux probes the path and tells you whether '
             'bytes crossed it. **g** gives up and shows the answer.'),
            ('If it says it cannot verify',
             'Some kernels forbid the unprivileged namespaces this needs. '
             'Where that is true the track says so and scores nothing, rather '
             'than pretending.'),
            ('How you are scored',
             'The path opened, or it did not: proven by a real probe '
             'from where it has to succeed.'),
        ],
    ),
    'chain': (
        'chain: a whole box, end to end',
        [
            ('What you are doing',
             'One engagement carried through all three tracks: sift the scan '
             'for the way in, salvage the exploit to land a shell, conduit '
             'from that shell to the next host. The story runs through all '
             'three.'),
            ('How to play',
             'Each stage plays exactly like its own track. Finish a stage and '
             'it bridges to the next. A stumble does not end the run: '
             'you reach all three stages, and the result is honest about '
             'which fell.'),
        ],
    ),
}


class HelpScreen(ScrollScreen):
    def __init__(self, topic: str | None = None) -> None:
        super().__init__()
        self.topic = topic

    @property
    def title(self) -> str:
        return f'{APP_TITLE}: help'

    def content(self, caps: Caps) -> list[Text]:
        p = caps.palette
        rows: list[Text] = []

        topic = _TOPICS.get(self.topic or '')
        if topic:
            heading, items = topic
            rows.append(line(f'  {heading}', p.accent, bold=True))
            rows.append(Text())
            for label, text in items:
                rows.append(line(f'  {label}', p.accent2, bold=True))
                rows.extend(wrap_rich(caps, text, caps.cols - 8, '    ',
                                      p.fg, p.accent))
                rows.append(Text())
        else:
            rows.extend(wrap_rich(caps, _ABOUT, caps.cols - 6, '  ',
                                  p.fg, p.accent))
            rows.append(Text())

        rows.extend(wrap_rich(caps, _REAL, caps.cols - 6, '  ', p.muted,
                              p.accent))
        rows.append(Text())
        rows.append(line('  Verification tiers', p.accent, bold=True))
        for t in TIERS:
            rows.append(line(f'    {t:<10}{TIER_MEANING[t]}', p.muted))
        rows.append(Text())
        rows.append(line('  Keys', p.accent, bold=True))
        keys = [('up / down, j / k', 'move')]
        if self.topic == 'sift':
            keys += [('space', 'mark or unmark a line'),
                     ('left / right', 'pan a wide line'),
                     ('enter', 'submit your marks')]
        elif self.topic in ('salvage', 'conduit'):
            keys += [('e', 'edit the script'), ('r', 'run it'),
                     ('g', 'give up and see the answer')]
        else:
            keys += [('enter', 'open')]
        keys += [('esc', 'back'), ('H', 'home'), ('q', 'quit')]
        for k, v in keys:
            rows.append(line(f'    {k:<20}{v}', p.muted))
        return rows

    def hints(self, caps: Caps) -> list[tuple[str, str]]:
        return self.scroll_hints(caps) + [('esc', 'back'), ('q', 'quit')]
