"""An instrumented HTTP service that crux owns (crux D2, D7).

**The trainer becomes the host.** Rather than pointing a student at somebody
else's machine, crux opens a listening socket on loopback, tells the exploit
where it is, and reads back what arrived. Nothing leaves this machine, the
target is made of sockets this process owns, and it is closed on teardown.

That is also what makes the tier `verified` rather than `self`: crux is not
taking your word for whether the exploit worked, it is the thing the exploit
was aimed at.

**The service is fictional and so is its vulnerability (crux D7).** There is
no real product here and no working exploit for real software in this
repository. What is real is the *defect class* in the script you are handed: a
Python 2 idiom, a hardcoded callback, a moved endpoint, a missing header, a
payload that needs encoding differently. Those transfer completely, and none
of them gets less educational for pointing at an invented CMS.

**Port zero, always.** The kernel picks the port and crux tells the scenario
what it got. A fixed port is a port that is occupied on somebody's machine one
day in fifty, and it is also how two crux runs would collide.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ._hits import HitRecord, Request, Requirement


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'Wexler/2.1'
    sys_version = ''

    def log_message(self, *args) -> None:
        """Silence. The default writes to stderr and would tear the TUI apart."""

    # -- plumbing ----------------------------------------------------------

    def _read(self) -> Request:
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else b''
        return Request(
            method=self.command,
            target=self.path,
            headers=tuple((k, v) for k, v in self.headers.items()),
            body=body,
            raw=body,
        )

    def _respond(self, req: Request) -> None:
        target = self.server.crux_target           # type: ignore[attr-defined]
        record = target.record
        record.record(req)

        met = record.met(req)
        if len(met) == len(record.requirements):
            payload = {'status': 'ok', 'result': target.success_token}
            code = 200
        elif req.route == target.route:
            payload = {'status': 'error', 'message': target.reject_message}
            code = target.reject_code
        else:
            payload = {'status': 'error', 'message': 'Not Found'}
            code = 404

        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    # -- verbs -------------------------------------------------------------

    def do_GET(self) -> None:
        self._respond(self._read())

    def do_POST(self) -> None:
        self._respond(self._read())

    def do_PUT(self) -> None:
        self._respond(self._read())

    def do_HEAD(self) -> None:
        self._respond(self._read())


class MockHttp:
    """A loopback HTTP service that scores what arrives.

    Use as a context manager, or call `start`/`stop`. `stop` is idempotent,
    because a screen can be torn down by a quit from three levels up and a
    leaked listener outlives the run that made it.
    """

    def __init__(self, requirements: tuple[Requirement, ...],
                 route: str = '/', success_token: str = 'CRUX-LANDED',
                 reject_code: int = 400,
                 reject_message: str = 'Bad request') -> None:
        self.record = HitRecord(requirements)
        self.route = route
        self.success_token = success_token
        self.reject_code = reject_code
        self.reject_message = reject_message
        self._srv: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> int:
        if self._srv is not None:
            return self.port
        srv = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        srv.daemon_threads = True
        srv.crux_target = self                     # type: ignore[attr-defined]
        self._srv = srv
        self._thread = threading.Thread(target=srv.serve_forever,
                                        kwargs={'poll_interval': 0.05},
                                        daemon=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        srv, self._srv = self._srv, None
        if srv is None:
            return
        srv.shutdown()
        srv.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> MockHttp:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- state -------------------------------------------------------------

    @property
    def port(self) -> int:
        return self._srv.server_address[1] if self._srv else 0

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self.port}'

    def verdict(self) -> tuple[bool, str, int]:
        return self.record.verdict()
