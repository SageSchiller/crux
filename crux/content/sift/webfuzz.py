"""sift: reading a content-discovery run.

Three scenarios. Where a port scan is short and mostly furniture, this output
is long and *entirely* furniture except for one or two rows, which makes it the
purest form of the skill: the eye has to learn what an anomaly looks like when
two hundred lines all look the same.

The tells here are structural rather than semantic. You are not reading the
path names for meaning so much as reading the **columns** for a number that
does not match its neighbours.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import FeroxRun, Hit

BOXES = 'Boxes/Linux'

# --------------------------------------------------------------------------
# 1. A size that does not match its neighbours
# --------------------------------------------------------------------------

_SIZE = MarkBody(
    prompt='A content-discovery run against the application root. Mark every '
           'line that changes what you do next.',
    fixture=FeroxRun(
        host='siteisup.htb',
        noise=(16, 24),
        hits=(
            Hit('/dev', 200, 14877, kind='lead', exact=True),
            Hit('/uploads', 301, kind='decoy'),
            Hit('/admin', 403, kind='decoy'),
        ),
    ),
    actions=(
        Action('Request `/dev` and read what is there.', True,
               'A 200 on a path that is not part of the site is the whole '
               'finding. `dev` directories are left behind, not deployed, and '
               'what is in them was never meant to be reachable.'),
        Action('Try to list `/uploads`, since uploads are usually writable.',
               why='A 301 to a directory that almost certainly returns a '
                   'listing or an index page. Worth a look, but "uploads '
                   'exist" is not a finding until you have somewhere to '
                   'upload from.'),
        Action('Attack `/admin`: it returns 403, so it is protected and '
               'therefore valuable.',
               why='The seductive one. A 403 does prove the path exists, '
                   'which is worth knowing, but a forbidden admin panel with '
                   'no credential and no bypass is a wall. `/dev` is open.'),
        Action('Re-run with a larger wordlist and more extensions first.',
               why='The reflex that eats exam time. You already have a hit '
                   'you have not read. Read it before you ask for more.'),
    ),
    debrief='In this output the tell is usually a **number, not a name**. '
            'Status codes cluster: a wall of 301s and 403s is the shape of a '
            'normal site. A 200 on a path that is not part of the '
            'application, or a size that does not match the other responses '
            'of its status, is where you look first.',
)

# --------------------------------------------------------------------------
# 2. A 403 that is worth more than the 200s
# --------------------------------------------------------------------------

_FORBIDDEN = MarkBody(
    prompt='Content discovery against a host running an ordinary-looking '
           'site. Mark every line that changes what you do next.',
    fixture=FeroxRun(
        host='10.10.11.108',
        noise=(18, 26),
        hits=(
            Hit('/.git', 403, kind='lead'),
            Hit('/phpmyadmin', 403, kind='decoy'),
            Hit('/backup', 301, kind='decoy'),
        ),
    ),
    actions=(
        Action('Try to pull the repository: `/.git/HEAD`, then dump it if the '
               'objects are readable.', True,
               'A 403 on `/.git` means the directory is **there**. The server '
               'refuses to list it, which says nothing about whether the '
               'files inside it can be fetched directly, and a readable '
               '`.git` is the entire source tree plus its history.'),
        Action('Brute-force the phpMyAdmin login.',
               why='A real install and a real wall. Guessing database '
                   'credentials against a login page is the slowest path on '
                   'this screen.'),
        Action('Enumerate `/backup` for archive filenames.',
               why='Reasonable and often productive, but it is a guessing '
                   'game about names. The `.git` directory has a known '
                   'internal layout you do not have to guess at.'),
        Action('Nothing useful: every interesting path returns 403.',
               why='The mistake this scenario is built around. **403 is not a '
                   'dead end, it is an existence proof.** A 404 says nothing '
                   'is there; a 403 says something is there and the server '
                   'would rather not discuss it.'),
    ),
    debrief='A 403 tells you the path **exists**, which is more than a 200 on '
            'a page everyone can see. The question is never "am I allowed to '
            'list this", it is "is there a file inside it whose name I '
            'already know". For `.git`, `.svn`, and `.DS_Store`, you always '
            'know the names.',
)

# --------------------------------------------------------------------------
# 3. Everything is the same size (crux D9)
# --------------------------------------------------------------------------

_WILDCARD = MarkBody(
    prompt='Content discovery against a single-page application. Mark every '
           'line that changes what you do next.',
    fixture=FeroxRun(
        host='app.mirage.vl',
        noise=(20, 28),
        wildcard_size=4242,
        hits=(
            Hit('/api', 200, kind='decoy'),
            Hit('/dashboard', 200, kind='decoy'),
            Hit('/settings', 200, kind='decoy'),
        ),
    ),
    actions=(
        Action('Nothing here is real. Filter on the repeated size and run it '
               'again.', True,
               'Every 200 is the same length, which is one page answering to '
               'every name: a catch-all route or a soft 404. Until that is '
               'filtered out the run has found nothing, no matter how many '
               'rows it printed.'),
        Action('Work through the 200s one at a time, starting with `/api`.',
               why='Each one will serve you the same front-end shell. This is '
                   'how an hour disappears into a wall of identical pages.'),
        Action('The application clearly has a large API surface: enumerate '
               '`/api` endpoints.',
               why='A conclusion drawn from a route that answers to every '
                   'name. `/api` here is no more real than `/settings`.'),
        Action('Re-run with `-x php,html,txt` to find the real files.',
               why='The catch-all answers those too. Extensions do not help '
                   'when the server is not routing on paths at all.'),
    ),
    debrief='**Identical sizes across unrelated paths means the server is not '
            'routing on paths.** Nothing on this screen is a finding, and the '
            'correct answer is to mark nothing and change the run: filter the '
            'repeated length and see what survives. A tool that reports two '
            'hundred hits has not found two hundred things.',
)

SCENARIOS = [
    Scenario(id='sift-web-size', track='sift', tier='graded', order=110,
             title='Content discovery, one row out of place',
             body=_SIZE, waypoint='web-discovery', hone=('ffuf', 'gobuster'),
             source=f'{BOXES}/HackTheBox/SiteIsUp/SiteIsUp - Writeup.md'),
    Scenario(id='sift-web-forbidden', track='sift', tier='graded', order=120,
             title='Everything interesting returns 403',
             body=_FORBIDDEN, waypoint='web-discovery',
             hone=('ffuf', 'gobuster'),
             source=f'{BOXES}/HackTheBox/Nunchucks/Nunchucks - Writeup.md'),
    Scenario(id='sift-web-wildcard', track='sift', tier='graded', order=130,
             title='Two hundred hits and the same number in every row',
             body=_WILDCARD, waypoint='web-baseline',
             hone=('ffuf', 'gobuster'),
             source='Boxes/00 - Privesc Quick Reference.md'),
]
