"""App-wide constants.

Small on purpose. Anything that grows a policy belongs in the module that owns
that policy, not here.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = 'crux'
APP_TITLE = 'CRUX'

#: Joined with the glyph-set bullet at render time. Kept as parts rather than
#: one string because a literal separator here would survive into the ASCII
#: rung, which is a bug class the sibling codebase hit more than once.
#:
#: The three parts are the three tracks read as a sentence, which is also the
#: order of a real engagement: see the thing, make the thing work, reach the
#: next thing. A tagline that counted scenarios would go stale every time the
#: content moved, and a number is not a promise.
#:
#: Must stay under 38 columns joined: `test.py` renders it at 40x16.
TAGLINE_PARTS = ('spot it', 'fix it', 'reach it')

#: The chord that always leaves a screen that is capturing raw input. No
#: scenario may claim it, which `validate.py` enforces.
EXIT_CHORD = 'F10'

#: Content is authored to fit here, and `test.py` asserts no screen overflows.
MIN_COLS = 80
MIN_ROWS = 24

#: The three tracks, in engagement order. The program name deliberately does
#: not enumerate them (crux D5): `proctor` and `lineage` are planned as four
#: and five, and adding one must cost nothing but a row here.
TRACKS = ('sift', 'salvage', 'conduit')

#: Chain mode composes the three tracks into one engagement. It is not a fourth
#: skill track (that is what `proctor` and `lineage` will be); it is the reason
#: the three are one program. Kept separate from TRACKS so everything that
#: means "the three skills" stays meaning exactly that, and SECTIONS is what
#: means "everything with content".
CHAIN = 'chain'
SECTIONS = TRACKS + (CHAIN,)

TRACK_BLURB = {
    'sift': 'Find the lead in raw tool output.',
    'salvage': 'Repair a broken proof-of-concept until it lands.',
    'conduit': 'Build the tunnel chain that reaches the next subnet.',
    'chain': 'One engagement, all three tracks, end to end.',
}

#: The verification tiers of crux D6. Never blurred, always shown.
TIERS = ('verified', 'graded', 'self')

TIER_MEANING = {
    'verified': 'crux watched the real end state',
    'graded': 'crux checked your answer against a key',
    'self': 'crux cannot read this back and says so',
}


def data_dir() -> Path:
    """Where state lives, per crux D16. Honours XDG, falls back to the spec."""
    base = os.environ.get('XDG_DATA_HOME') or (Path.home() / '.local' / 'share')
    return Path(base) / APP_NAME


def state_path() -> Path:
    return data_dir() / 'state.json'


#: Where the local writeup corpus lives, for the provenance audit of crux
#: D11. A machine-specific path, never shown to anyone: the app itself
#: never reads it and content must run on a machine that has never seen it.
#: Never read by the app itself: content carries its own text, and a scenario
#: must run on a machine that has never seen the vault. Only `validate.py`
#: looks, and only to check that a cited path is a real file.
VAULT_ENV = 'CRUX_VAULT'
VAULT_FILE = '.crux-vault'
_VAULT_DEFAULT = (
    Path.home() / 'Documents' / 'Main' / 'Cyber Security Study and Reference'
    / 'OffSec' / 'Pen-200'
)


def vault_dir() -> Path | None:
    """The writeup root, or None when it is not reachable from here.

    Three places, in order: `$CRUX_VAULT`, a git-ignored `.crux-vault` file
    beside the repository holding the path, then the author's own location.
    None is a normal answer, not an error: on any other machine the audit
    simply does not run.
    """
    raw = os.environ.get(VAULT_ENV)
    if not raw:
        marker = Path(__file__).resolve().parent.parent / VAULT_FILE
        if marker.exists():
            raw = marker.read_text(encoding='utf-8').strip()
    candidate = Path(raw).expanduser() if raw else _VAULT_DEFAULT
    return candidate if candidate.is_dir() else None
