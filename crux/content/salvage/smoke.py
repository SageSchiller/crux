"""Phase 0 placeholder. The salvage engine lands in Phase 3.

Carries `self` tier and says on screen that nothing is being checked, which is
crux D6 and D14 applied to the app's own incompleteness. An honesty rule that
does not bind when it is merely inconvenient does not bind.
"""

from __future__ import annotations

from ...model import Scenario, StubBody

SCENARIOS = [
    Scenario(
        id='salvage-smoke',
        track='salvage',
        title='Engine not built yet',
        tier='self',
        order=0,
        body=StubBody(
            prompt='salvage stands up an instrumented mock service on '
                   'loopback and hands you a proof-of-concept that does not '
                   'work. You fix it in your own editor and run it; crux '
                   'reads the service hit record and tells you whether it '
                   'landed.',
            phase='Phase 3',
            debrief='Defect classes 1 to 5 (Python 2 idioms, hardcoded '
                    'callback, moved endpoint, missing header, encoding) land '
                    'in Phase 3. Classes 6 to 10 land in Phase 4, ending on '
                    'the hostile-PoC capstone of crux D19.',
        ),
    ),
]
