"""Scenario discovery.

Content is organised by track, so a file under `crux/content/<track>/` that
defines `SCENARIOS` appears in that track. Nothing lists the files by hand.
`pkgutil.iter_modules` is used rather than a filesystem walk because it works
unchanged inside the zipapp, which is the only form most people will run.

**Loading is tolerant and reporting.** A content file that fails to import does
not take the app down; it is recorded as a load error that the UI and
`validate.py` both show. A track with no scenarios at all is a valid state the
track picker must render, not a failure: during Phase 0 that is nearly all of
them.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field

from .config import TRACK_BLURB, TRACKS
from .model import ContentError, Scenario, Track

CONTENT_PACKAGE = 'crux.content'


@dataclass
class Registry:
    tracks: dict[str, Track] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def scenarios(self) -> list[Scenario]:
        out: list[Scenario] = []
        for name in TRACKS:
            out.extend(self.tracks[name].scenarios)
        return out

    def by_id(self, scenario_id: str) -> Scenario | None:
        for s in self.scenarios:
            if s.id == scenario_id:
                return s
        return None

    def track(self, name: str) -> Track:
        return self.tracks[name]


def _load_track(name: str, errors: list[str]) -> Track:
    track = Track(name=name, blurb=TRACK_BLURB.get(name, ''))
    pkg_name = f'{CONTENT_PACKAGE}.{name}'
    try:
        pkg = importlib.import_module(pkg_name)
    except ImportError as e:
        errors.append(f'{pkg_name}: {e}')
        return track

    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda i: i.name):
        if info.name.startswith('_'):
            continue
        mod_name = f'{pkg_name}.{info.name}'
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:                      # content bug, not app bug
            errors.append(f'{mod_name}: {e.__class__.__name__}: {e}')
            continue
        found = getattr(mod, 'SCENARIOS', None)
        if found is None:
            errors.append(f'{mod_name}: no SCENARIOS')
            continue
        for s in found:
            if not isinstance(s, Scenario):
                errors.append(f'{mod_name}: {s!r} is not a Scenario')
                continue
            if s.track != name:
                errors.append(f'{s.id}: lives in {name}/ but declares track {s.track!r}')
                continue
            track.scenarios.append(s)

    track.scenarios.sort(key=lambda s: (s.order, s.id))
    return track


def load() -> Registry:
    """Load every track. Never raises: errors are collected and reported."""
    reg = Registry()
    for name in TRACKS:
        reg.tracks[name] = _load_track(name, reg.errors)

    seen: dict[str, str] = {}
    for s in reg.scenarios:
        if s.id in seen:
            reg.errors.append(f'duplicate scenario id {s.id!r}')
        seen[s.id] = s.track
    return reg
