"""Say that a scenario is drawn from a real attack chain, without naming
anybody else's material.

**The rule (crux D23).** crux names the techniques and, where one applies, the
CVE. It does not name training platforms, courses, vendors or the individual
machines its scenarios were modelled on. Two reasons, and the second is the one
that matters. The exercises stand on the technique being real, not on whose lab
it appeared in, so the attribution adds nothing a student can use. And crux is
meant to be handed to anyone, which a wall of somebody else's product names
quietly prevents.

The `source` field on a scenario still records exactly where it came from,
because `validate.py` audits it and that audit has caught real errors. It is
authoring metadata: it is never rendered, and this module is the only thing
that turns it into anything a person sees.
"""

from __future__ import annotations

#: What a scenario modelled on one specific engagement is called on screen.
FROM_CHAIN = 'a real attack chain'

#: What a scenario distilled from technique rather than one engagement is
#: called. Still real, still not attributed.
FROM_TRADECRAFT = 'real-world tradecraft'


def _is_playbook(parts: list[str]) -> bool:
    return any('Playbook' in p for p in parts)


def based_on(source: str) -> str:
    """A short, non-attributing label for where a scenario comes from.

    Returns '' when the scenario records no source at all, so a screen can
    leave the line off rather than claim something.
    """
    if not source:
        return ''
    parts = [p for p in source.replace('\\', '/').split('/') if p]

    # Distilled from technique notes rather than from one engagement.
    if _is_playbook(parts):
        return FROM_TRADECRAFT

    # A specific engagement: `.../<Box>/<Box> - Writeup.md`.
    last = parts[-1] if parts else ''
    if last.endswith('.md') and ' - ' in last:
        name = last.rsplit(' - ', 1)[0].strip()
        # A numbered index note is a reference, not an engagement.
        if name and not name[0].isdigit():
            return FROM_CHAIN
        return FROM_TRADECRAFT
    return FROM_TRADECRAFT


def is_specific_chain(source: str) -> bool:
    """True when the scenario is modelled on one engagement end to end."""
    return based_on(source) == FROM_CHAIN
