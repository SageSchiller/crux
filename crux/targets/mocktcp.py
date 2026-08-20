"""An instrumented raw TCP service that crux owns (crux D2, D7).

The same contract as `mockhttp.MockHttp`, for the scenarios whose defect is
below HTTP: a length prefix, a delimiter, a protocol handshake, a payload that
has to arrive as bytes rather than as a string. Both expose `start`, `stop`,
`port`, and `verdict`, so a scenario can move between them and neither the
screen nor the scoring has to know which it is talking to.

Reads are bounded and the socket has a timeout, because a mock target that a
half-finished exploit can hang forever is a mock target that hangs crux.
"""

from __future__ import annotations

import socket
import threading

from ._hits import HitRecord, Request, Requirement

MAX_PAYLOAD = 64 * 1024
READ_TIMEOUT = 2.0


class MockTcp:
    def __init__(self, requirements: tuple[Requirement, ...],
                 banner: bytes = b'', success_token: str = 'CRUX-LANDED',
                 reject: bytes = b'ERR unrecognised command\n') -> None:
        self.record = HitRecord(requirements)
        self.banner = banner
        self.success_token = success_token
        self.reject = reject
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> int:
        if self._sock is not None:
            return self.port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 0))
        s.listen(8)
        s.settimeout(0.2)
        self._sock = s
        self._stop.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def __enter__(self) -> MockTcp:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- serving -----------------------------------------------------------

    def _serve(self) -> None:
        while not self._stop.is_set():
            sock = self._sock
            if sock is None:
                return
            try:
                conn, _ = sock.accept()
            except (TimeoutError, OSError):
                continue
            threading.Thread(target=self._handle, args=(conn,),
                             daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        """Read lines until the peer stops, answering each one.

        **A line at a time, not a single read.** The first version stopped at
        the first newline, which broke the only thing this target exists to
        model: a daemon that wants an authentication line *before* it will
        look at the command on the next one. A script that sent both got
        graded on the first, so the reference solution for the handshake
        scenario failed while the broken one it was supposed to fix scored
        higher. A mock service has to speak the protocol it claims to.

        Every line seen so far is accumulated, and the requirements are
        checked against the accumulation, so state built up over several lines
        counts. One `Request` per connection is recorded at the end, holding
        everything the peer said.
        """
        with conn:
            conn.settimeout(READ_TIMEOUT)
            if self.banner:
                try:
                    conn.sendall(self.banner)
                except OSError:
                    return

            buf = b''
            seen = b''
            slot = -1
            try:
                while len(seen) < MAX_PAYLOAD:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b'\n' in buf:
                        one, buf = buf.split(b'\n', 1)
                        seen += one + b'\n'
                        slot = self._answer(conn, seen, slot)
            except (TimeoutError, OSError):
                pass
            if buf:                       # a final line with no terminator
                seen += buf
                self._answer(conn, seen, slot)

    def _answer(self, conn: socket.socket, seen: bytes, slot: int) -> int:
        """Record what has been said so far, **then** reply.

        The order is the whole point. Recording when the connection closed
        instead meant a client could read `OK` and ask crux for the verdict
        before the server thread had written it down, and the screen does
        exactly that: it reads `verdict()` the moment the exploit subprocess
        exits. Recording first makes a received reply a guarantee that the
        record is already updated, so there is no race to lose.

        One entry per connection, replaced as lines accumulate, so a two-line
        handshake is one request that grew rather than two half-requests.
        """
        req = Request(method='', target='', body=seen, raw=seen)
        if slot < 0:
            self.record.record(req)
            slot = len(self.record.requests) - 1
        else:
            self.record.requests[slot] = req

        ok = len(self.record.met(req)) == len(self.record.requirements)
        try:
            conn.sendall(f'OK {self.success_token}\n'.encode()
                         if ok else self.reject)
        except OSError:
            pass
        return slot

    # -- state -------------------------------------------------------------

    @property
    def port(self) -> int:
        return self._sock.getsockname()[1] if self._sock else 0

    def verdict(self) -> tuple[bool, str, int]:
        return self.record.verdict()
