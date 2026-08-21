"""Everything that survives a session, and how to throw it away.

Progress is two separate things, and a reset that only cleared one of them
would be a lie:

* **History** is `state.json`: every attempt, its score and its time on task.
* **Work** is `work/<scenario>/`: the exploit and tunnel scripts you edited,
  and the generated SSH keypair `conduit` uses.

**Why the work files needed fixing before a reset could mean anything.**
`salvage` rewrote your script from the original every time you opened the
scenario, so your repairs were silently destroyed between visits; `conduit`
never rewrote it, so a mangled script could never be recovered. One threw away
your work, the other trapped you in it, and neither could be reset. Both now
keep the file and both can restore the original on request.

Keeping the file has one wrinkle worth stating, because it is the reason this
module exists rather than a one-line `if not exists`. The mock target takes an
**ephemeral port**, so the address crux substituted into your script last time
is dead by the time you come back. Rewriting the whole file would destroy your
edits; leaving it alone would point it at nothing. So crux records exactly
which strings it injected, in `.crux-meta.json` beside the script, and on
reopen replaces **only those**. Your edits survive untouched and the target
still answers.

That precision matters: one `salvage` scenario is about a hardcoded callback
address of `127.0.0.1:4444` that the student must *keep*, so a blunt
"rewrite anything that looks like a local address" would break the exercise it
was meant to help.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import data_dir, state_path

META = '.crux-meta.json'


# --------------------------------------------------------------------------
# Work files
# --------------------------------------------------------------------------

def work_root() -> Path:
    return data_dir() / 'work'


def scenario_dir(scenario_id: str) -> Path:
    return work_root() / scenario_id


def _read_meta(d: Path) -> dict:
    try:
        return json.loads((d / META).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _write_meta(d: Path, subs: dict) -> None:
    try:
        (d / META).write_text(json.dumps(subs, indent=1, sort_keys=True),
                              encoding='utf-8')
    except OSError:
        pass


def _retarget(text: str, old: dict, new: dict) -> str:
    """Swap the strings crux injected last time for this run's."""
    for key, was in old.items():
        now = new.get(key)
        if not was or not now or was == now:
            continue
        if key == 'port':
            # A bare number, so match it as a whole token. Replacing the digits
            # anywhere would be free to corrupt a timeout or a buffer size.
            text = re.sub(rf'\b{re.escape(str(was))}\b', str(now), text)
        else:
            text = text.replace(was, now)
    return text


def prepare(scenario_id: str, filename: str, fresh_text: str,
            subs: dict) -> tuple[Path, bool]:
    """Return (path, was_created). Keeps an existing file, re-pointing it.

    `subs` maps a name to the string crux injected for this run: `url`, `sink`,
    `port`, `assets`. Whatever was injected last time is swapped for it.
    """
    d = scenario_dir(scenario_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    if not path.exists():
        path.write_text(fresh_text, encoding='utf-8')
        _write_meta(d, subs)
        return path, True

    old = _read_meta(d)
    if old:
        try:
            text = path.read_text(encoding='utf-8')
            fixed = _retarget(text, old, subs)
            if fixed != text:
                path.write_text(fixed, encoding='utf-8')
        except OSError:
            pass
    _write_meta(d, subs)
    return path, False


def restore(scenario_id: str, filename: str, fresh_text: str,
            subs: dict) -> Path:
    """Throw away the edited script and write the original back."""
    d = scenario_dir(scenario_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(fresh_text, encoding='utf-8')
    _write_meta(d, subs)
    return path


# --------------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Summary:
    """What a reset would actually remove. Shown before anything is deleted."""

    attempts: int
    scenarios_played: int
    work_scenarios: int
    has_assets: bool

    @property
    def anything(self) -> bool:
        return bool(self.attempts or self.work_scenarios or self.has_assets)

    def history_line(self) -> str:
        if not self.attempts:
            return 'no attempts recorded'
        return (f'{self.attempts} attempt'
                f'{"" if self.attempts == 1 else "s"} across '
                f'{self.scenarios_played} scenario'
                f'{"" if self.scenarios_played == 1 else "s"}')

    def work_line(self) -> str:
        if not self.work_scenarios and not self.has_assets:
            return 'no saved exercise files'
        bits = []
        if self.work_scenarios:
            bits.append(f'{self.work_scenarios} edited script'
                        f'{"" if self.work_scenarios == 1 else "s"}')
        if self.has_assets:
            bits.append('the generated SSH keypair')
        return ' and '.join(bits)


def summary(state=None) -> Summary:
    """What is on disk right now. Never raises: a missing directory is zero."""
    if state is None:
        from .state import State
        state = State.load()
    attempts = len(state.attempts)
    played = len({a.scenario for a in state.attempts})

    scenarios = 0
    assets = False
    root = work_root()
    try:
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if child.name == '_assets':
                assets = True
            elif any(child.iterdir()):
                scenarios += 1
    except OSError:
        pass
    return Summary(attempts=attempts, scenarios_played=played,
                   work_scenarios=scenarios, has_assets=assets)


def clear_history() -> bool:
    """Delete recorded attempts. True if a file was actually removed."""
    p = state_path()
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def clear_work() -> bool:
    """Delete every edited script and the generated keypair."""
    root = work_root()
    try:
        if not root.exists():
            return False
        shutil.rmtree(root)
        return True
    except OSError:
        return False
