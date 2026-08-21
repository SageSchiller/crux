"""sift: reading a single HTTP response.

Two scenarios. Unlike a scan or a discovery run, there is no repetition here
to find an outlier in: the screen is short and every line is different. The
skill is knowing **which headers carry consequences** and which are the
protocol talking to itself, and remembering that page source is output a
developer wrote rather than output a tool generated.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import HttpResponse, Note

BOXES = 'Boxes/Linux'
PLAYBOOK = 'PEN-200 Playbook'

_HEADERS = MarkBody(
    prompt='The response to `curl -i` against the application root. Mark '
           'every line that changes what you do next.',
    fixture=HttpResponse(
        status='HTTP/1.1 200 OK',
        headers=(
            Note('Server: Werkzeug/2.2.2 Python/3.9.2', 'lead',
                 why='The finding is the class of server, not the version. '
                     'Werkzeug is a development server that was never meant to '
                     'face a network; where one does, the interactive debugger '
                     'is one URL away and it is a Python shell.'),
            Note('X-Powered-By: Flask', 'decoy',
                 why='It says the same thing the Server header already did, '
                     'less precisely. Two headers agreeing is confirmation, '
                     'not two findings.'),
            Note('Set-Cookie: session=eyJ1c2VyIjoiZ3Vlc3QifQ.ZbQ; Path=/',
                 'decoy',
                 why='Genuinely worth decoding, and it will say '
                     '`{"user":"guest"}`. Forging one needs the signing key, '
                     'so it is the longer path of the two on this screen.'),
            Note('X-Frame-Options: SAMEORIGIN'),
            Note('X-Content-Type-Options: nosniff'),
        ),
    ),
    actions=(
        Action('Try `/console`: Werkzeug is a development server, and its '
               'debugger sometimes ships enabled.', True,
               'The finding is not the version, it is the **class of '
               'server**. Werkzeug is the Flask development server and was '
               'never meant to face a network; where it does, the interactive '
               'debugger is one URL away and it is a Python shell.'),
        Action('Decode the session cookie: it is base64 and may be forgeable.',
               why='Genuinely worth doing, and it will decode to '
                   '`{"user":"guest"}`. Flask signs these, so forging one '
                   'needs the secret key. Keep it, but the server line is the '
                   'shorter path.'),
        Action('`X-Powered-By: Flask` confirms the framework: search for '
               'Flask vulnerabilities.',
               why='It tells you the same thing the `Server` header already '
                   'did, less precisely. Two headers agreeing is '
                   'confirmation, not two findings, and "vulnerabilities in '
                   'Flask" is not a plan.'),
        Action('`X-Frame-Options` and `X-Content-Type-Options` are set, so '
               'note the app is reasonably hardened and move on.',
               why='Both are browser-side hints about rendering. They have no '
                   'bearing on anything you can do to the server, and their '
                   'presence says nothing about how it is configured.'),
    ),
    debrief='**Ask what class of software a header names, not just what '
            'version.** `Werkzeug`, `WEBrick`, `SimpleHTTPServer` and '
            '`webpack-dev-server` are development servers, and finding one '
            'answering the internet means somebody deployed a debug build. '
            'Security headers like `X-Frame-Options` are noise from your side '
            'of the connection entirely.',
)

_SOURCE = MarkBody(
    prompt='The source of the login page. Mark every line that changes what '
           'you do next.',
    fixture=HttpResponse(
        status='HTTP/1.1 200 OK',
        headers=(
            Note('Server: Apache/2.4.58 (Ubuntu)'),
            Note('Content-Type: text/html; charset=UTF-8'),
        ),
        noise=(2, 3),
        source=(
            Note('<!DOCTYPE html>'),
            Note('<html lang="en"><head><meta charset="utf-8">'),
            Note('<title>Bertram Industrial - Sign in</title>'),
            Note('<link rel="stylesheet" href="/css/bootstrap.min.css">'),
            Note('<!-- TODO: remove test account before go-live '
                 '(svc_test / Wint3r2025!) -->', 'lead',
                 why='A developer left working credentials in a comment that '
                     'ships to every visitor. Spray the pair at SSH and any '
                     'other login before spending it on this form.'),
            Note('</head><body>'),
            Note('<form action="/auth.php" method="post">'),
            Note('  <input type="text" name="username" id="username">'),
            Note('  <input type="password" name="password" id="password">'),
            Note('  <input type="hidden" name="csrf" value="a91f0c22b7">',
                 'decoy',
                 why='Attacking a CSRF token means attacking a defence against '
                     'an attack you are not performing. You want to log in, '
                     'not to make somebody else log in.'),
            Note('  <button type="submit">Sign in</button>'),
            Note('</form>'),
            Note('<script src="/js/app.min.js"></script>', 'decoy',
                 why='A genuinely good habit and often productive, but it is a '
                     'search, and there is a working credential four lines '
                     'above it.'),
            Note('</body></html>'),
        ),
    ),
    actions=(
        Action('Log in as `svc_test` with the password in the comment, and '
               'try the same pair everywhere else on the box.', True,
               'A developer left working credentials in a comment that ships '
               'to every visitor. It is the whole finding, and the pair is '
               'worth spraying at SSH and any other login before it is spent '
               'on this form.'),
        Action('Read `/js/app.min.js` for hidden API endpoints.',
               why='A genuinely good habit and often productive, which is why '
                   'it is here. But it is a search, and there is a working '
                   'credential four lines above it.'),
        Action('The CSRF token is short and looks predictable: try to '
               'forge one.',
               why='Attacking a CSRF token means attacking a defence against '
                   'an attack you are not performing. You want to log in, not '
                   'to make somebody else log in.'),
        Action('Note that the form posts to `/auth.php` and fuzz it for SQL '
               'injection.',
               why='Reasonable, and where you go **after** the credential '
                   'fails. Reading the source before attacking the form is '
                   'the point of having read the source.'),
    ),
    debrief='**Page source is written by a person; a scan is written by a '
            'tool.** Comments, hidden inputs, commented-out blocks and '
            'referenced script paths are all working notes somebody left, and '
            'the single highest-yield habit in web enumeration is to read the '
            'source of every page you land on before you attack the form on '
            'it.',
)

SCENARIOS = [
    Scenario(id='sift-http-headers', track='sift', tier='graded', order=710,
             title='Response headers from the application root',
             body=_HEADERS, waypoint='web-baseline', hone=('curl',),
             source=f'{PLAYBOOK}/03 - Phase 3 - Web Enumeration & Fuzzing.md'),
    Scenario(id='sift-http-source', track='sift', tier='graded', order=720,
             title='The source of a login page',
             body=_SOURCE, waypoint='web-review', hone=('curl',),
             source=f'{PLAYBOOK}/03 - Phase 3 - Web Enumeration & Fuzzing.md'),
]
