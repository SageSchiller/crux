"""Turn a scenario's `source` path into a readable "based on" line.

The point is honesty made visible. Every `sift` scenario is modelled on a real
PEN-200 box or on the course methodology, and the `source` field has always
recorded which, but nothing showed it, so the exercises read as invented when
they are not. This parses the stored path into a short label the screens can
show: `Busqueda (HackTheBox)`, `Nibbles (Proving Grounds)`, or, for a scenario
drawn from the methodology rather than one box, `PEN-200 methodology`.

Pure and dependency-free: it reads the path string, never the vault. A machine
that has never seen the writeups still shows the right label.
"""

from __future__ import annotations

import re

_PLATFORMS = {
    'HackTheBox': 'HackTheBox',
    'Proving Grounds Play': 'Proving Grounds',
    'Proving Grounds': 'Proving Grounds',
    'VulnLab': 'VulnLab',
    'ProLabs': 'HackTheBox Pro Labs',
}


def based_on(source: str) -> str:
    """A short human label for where a scenario comes from. '' if unknown."""
    if not source:
        return ''
    parts = [p for p in source.replace('\\', '/').split('/') if p]

    # A specific box: .../<Platform>/<Box>/<Box> - Writeup.md
    if parts and parts[-1].endswith('.md') and ' - ' in parts[-1]:
        box = parts[-1].rsplit(' - ', 1)[0].strip()
        platform = next((_PLATFORMS[p] for p in parts if p in _PLATFORMS), '')
        if box and box[0].isdigit():
            box = ''                                  # a numbered index note
        if box:
            return f'{box} ({platform})' if platform else box

    # The methodology playbook.
    if 'PEN-200 Playbook' in parts:
        m = re.search(r'Phase \d+[a-z]? - (.+?)(?:\.md)?$', parts[-1])
        topic = m.group(1).strip() if m else ''
        return f'PEN-200 methodology: {topic}' if topic else 'PEN-200 methodology'

    # A shared reference note, or a whole category.
    last = parts[-1].replace('.md', '')
    if last == 'Active Directory':
        return 'PEN-200 Active Directory set'
    if 'Privesc' in last:
        return 'PEN-200 privilege-escalation reference'
    return 'PEN-200 course material'


def is_specific_box(source: str) -> bool:
    """True when the label names one real machine rather than the methodology."""
    label = based_on(source)
    return bool(label) and 'methodology' not in label and 'reference' not in label \
        and 'material' not in label and 'set' not in label
