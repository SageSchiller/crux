"""sift: reading a port scan.

Five scenarios. The through-line is that **a port scan is mostly furniture**,
and the skill is knowing which of two or three genuinely interesting lines is
the one that changes your next hour.

One of these has no lead at all (crux D9). It is not marked as such anywhere a
student can see, which is the point: the possibility has to stay live or the
app trains the instinct that every screen is hiding something.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import NmapScan, Note, Port

BOXES = 'Boxes/Linux'
PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# 1. The odd port whose SERVICE name is a guess
# --------------------------------------------------------------------------

_ODDPORT = MarkBody(
    prompt='A full TCP sweep, no version detection. Mark every line that '
           'changes what you do next.',
    fixture=NmapScan(
        version_scan=False,
        noise=(1, 3),
        ports=(
            Port(21, 'ftp', kind='decoy'),
            Port(22, 'ssh'),
            Port(80, 'http', kind='decoy'),
            Port(5437, 'pmip6-data', kind='lead'),
        ),
    ),
    actions=(
        Action('Point `-sV` at 5437 and find out what is actually listening.',
               True,
               'The only line here that a normal host would not have. '
               'Confirming the protocol is what turns "a weird high port" '
               'into "a database I can try vendor defaults against".'),
        Action('Try anonymous FTP on 21.',
               why='Real, and real furniture. FTP on 21 is on the top-1000 '
                   'list precisely because it is everywhere. It is worth ten '
                   'minutes, not first.'),
        Action('Start content discovery against the web server on 80.',
               why='Not wrong, just second. An ordinary HTTP server is a '
                   'maybe; a service on a port nothing normally uses is a '
                   'lead.'),
        Action('Nothing actionable: `pmip6-data` is not a service anyone runs.',
               why='The trap, and the reason this scenario exists. Without '
                   '`-sV`, that column is nmap reading a port-number lookup '
                   'table, not identifying anything. `pmip6-data` does not '
                   'mean "obscure protocol", it means **nobody normally '
                   'listens here**, which is the most interesting sentence '
                   'on the screen.'),
    ),
    debrief='Without `-sV` the SERVICE column is a guess from '
            '`/usr/share/nmap/nmap-services`, and a name you do not recognise '
            'is a **port nothing standard uses**, not a service to dismiss. '
            'On the box this comes from, PostgreSQL was on 5437 rather than '
            '5432, so a default top-1000 scan never saw it and left two '
            'rabbit holes and no path.',
)

# --------------------------------------------------------------------------
# 2. A pinned third-party product
# --------------------------------------------------------------------------

_PINNED = MarkBody(
    prompt='A full TCP scan with service detection has finished. Mark every '
           'line that changes what you do next.',
    fixture=NmapScan(
        noise=(0, 2),
        os_line='Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel',
        ports=(
            Port(22, 'ssh', 'OpenSSH 8.9p1 Ubuntu 3ubuntu0.4', kind='decoy'),
            Port(80, 'http', 'Apache httpd 2.4.52 ((Ubuntu))'),
            Port(111, 'rpcbind', '2-4 (RPC #100000)', kind='decoy',
                 state='filtered'),
            Port(3000, 'http', 'Gitea 1.19.1', kind='lead'),
        ),
    ),
    actions=(
        Action('Check Gitea 1.19.1 against its advisories, and browse it for '
               'public repositories.', True,
               'A named product at a pinned version is the most productive '
               'thing on this screen. Gitea also leaks repository and user '
               'names before you hold any credential at all.'),
        Action('Brute-force SSH with a common username list.',
               why='The classic rabbit hole. SSH is open on nearly every '
                   'Linux host and is almost never the way in. It gets parked '
                   'until a credential exists, not attacked because it is '
                   'there.'),
        Action('Investigate the filtered rpcbind on 111.',
               why='`filtered` is not `open`. A packet went out and nothing '
                   'came back, which is a firewall telling you nothing.'),
        Action('Content-discover the Apache on 80 before touching 3000.',
               why='Order matters when the clock is the opponent. The '
                   'unfingerprinted default Apache is a maybe; a '
                   'version-pinned third-party app is a lead.'),
    ),
    debrief='A **version-pinned third-party product** outranks a default '
            'service every time, and `filtered` is not `open`.',
)

# --------------------------------------------------------------------------
# 3. The lead is a name, not a port
# --------------------------------------------------------------------------

_CERT = MarkBody(
    prompt='Service detection against a host serving HTTPS. Mark every line '
           'that changes what you do next.',
    fixture=NmapScan(
        noise=(0, 2),
        ports=(
            Port(22, 'ssh', 'OpenSSH 9.2p1 Debian 2+deb12u3'),
            Port(80, 'http', 'nginx 1.22.1', scripts=(
                Note('|_http-title: Did not follow redirect to https://staging'
                     '.internal.corp/'),
                Note('|_http-server-header: nginx/1.22.1'),
            )),
            Port(443, 'ssl/http', 'nginx 1.22.1', scripts=(
                Note('| ssl-cert: Subject: commonName=staging.internal.corp',
                     'lead'),
                Note('| Subject Alternative Name: DNS:staging.internal.corp, '
                     'DNS:git.internal.corp', 'lead'),
                Note('| Not valid before: 2026-01-14T09:22:10'),
                Note('|_Not valid after:  2027-01-14T09:22:10'),
                Note('|_ssl-date: TLS randomness does not represent time'),
                Note('|_http-server-header: nginx/1.22.1', 'decoy'),
            )),
        ),
    ),
    actions=(
        Action('Add both names to `/etc/hosts` and request the site by name, '
               'starting with the one that is not already serving.', True,
               'The certificate is the server telling you its own names. '
               '`git.internal.corp` is not serving on the default vhost, '
               'which is exactly why it is worth asking for by name.'),
        Action('Fingerprint nginx 1.22.1 for known vulnerabilities.',
               why='A current, stock web server. The version is on the screen '
                   'three times, which is how you can tell it is furniture '
                   'rather than a finding.'),
        Action('Content-discover `https://<ip>/` directly.',
               why='You will get the default vhost and learn nothing. Name '
                   'resolution comes before content discovery when the server '
                   'has told you it answers to names.'),
        Action('Note the certificate dates and check whether it is expired.',
               why='Real observation, no consequence. An expired certificate '
                   'changes nothing about what you can reach.'),
    ),
    debrief='A TLS certificate is a **free hostname disclosure**. The Subject '
            'and the Subject Alternative Name list are the server naming '
            'itself, and a name in there that is not the one you connected to '
            'is a virtual host you have not seen yet. Let the server tell you '
            'the name; never guess it.',
)

# --------------------------------------------------------------------------
# 4. A scan that gives you nothing (crux D9)
# --------------------------------------------------------------------------

_QUIET = MarkBody(
    prompt='A full TCP scan with service detection has finished. Mark every '
           'line that changes what you do next.',
    fixture=NmapScan(
        noise=(0, 1),
        os_line='Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel',
        ports=(
            Port(22, 'ssh', 'OpenSSH 9.6p1 Ubuntu 3ubuntu13.5', kind='decoy'),
            Port(80, 'http', 'Apache httpd 2.4.58 ((Ubuntu))', scripts=(
                Note('|_http-title: Bertram Industrial Supplies'),
                Note('|_http-server-header: Apache/2.4.58 (Ubuntu)', 'decoy'),
            )),
        ),
    ),
    actions=(
        Action('Nothing here. Go to content discovery and read the site.',
               True,
               'Correct, and the harder call than it looks. Two current stock '
               'services and nothing pinned means **this scan is finished '
               'telling you things**. The path is in the web content, and the '
               'sooner you stop re-reading the scan the sooner you find it.'),
        Action('Search for exploits against OpenSSH 9.6p1.',
               why='Current, patched, and the single most reliable way to '
                   'spend an hour of an exam on nothing.'),
        Action('Re-run the scan with `-sU` for UDP, and with `--script vuln`.',
               why='Sometimes right, usually the shape of not wanting to '
                   'leave the scanning phase. You have two open ports and one '
                   'of them serves a web application you have not looked at.'),
        Action('Fingerprint Apache 2.4.58 for a known CVE.',
               why='It is the distribution build at the distribution version. '
                   'The server header saying the same thing as the version '
                   'column is confirmation, not a finding.'),
    ),
    debrief='**Some screens contain nothing, and saying so is the answer.** '
            'A scan of two current stock services has done its job by telling '
            'you where the application is. Marking something here because a '
            'screen must surely be hiding something is exactly the instinct '
            'that produces rabbit holes.',
)

# --------------------------------------------------------------------------
# 5. A domain controller announces itself
# --------------------------------------------------------------------------

_DC = MarkBody(
    prompt='Service detection against a Windows host. Mark every line that '
           'changes what you do next.',
    fixture=NmapScan(
        noise=(0, 1),
        ports=(
            Port(53, 'domain', 'Simple DNS Plus'),
            Port(88, 'kerberos-sec', 'Microsoft Windows Kerberos', kind='lead'),
            Port(135, 'msrpc', 'Microsoft Windows RPC'),
            Port(139, 'netbios-ssn', 'Microsoft Windows netbios-ssn'),
            Port(389, 'ldap', 'Microsoft Windows Active Directory LDAP '
                 '(Domain: hollow.vl)', kind='lead'),
            Port(445, 'microsoft-ds', '', kind='decoy'),
            Port(464, 'kpasswd5', ''),
            Port(593, 'ncacn_http', 'Microsoft Windows RPC over HTTP 1.0'),
            Port(3268, 'ldap', 'Microsoft Windows Active Directory LDAP '
                 '(Domain: hollow.vl)', kind='decoy'),
            Port(3389, 'ms-wbt-server', 'Microsoft Terminal Services',
                 kind='decoy'),
        ),
    ),
    actions=(
        Action('Treat this as a domain controller for `hollow.vl`: put the '
               'domain and host in `/etc/hosts`, sync time to it, and start '
               'unauthenticated enumeration.', True,
               'Kerberos on 88 with LDAP announcing a domain is a DC, and '
               'that reframes the whole box: the target stops being a host '
               'and becomes a directory. Clock skew breaks Kerberos, which is '
               'why time sync comes before anything else.'),
        Action('Focus on 3389 and try RDP with common credentials.',
               why='Present on most Windows servers and gets you nothing '
                   'without a credential. The identity infrastructure is the '
                   'target here, not the remote desktop.'),
        Action('Enumerate SMB shares on 445 first.',
               why='Not wrong, and it is a real next step, but it is one '
                   'branch of the DC realisation rather than the realisation '
                   'itself. Get the domain name and the time sync right '
                   'before you start collecting.'),
        Action('Note that 3268 is a second LDAP and scan it separately.',
               why='3268 is the Global Catalog on the same directory. It is '
                   'confirmation of what 389 already said, not a second '
                   'target.'),
    ),
    debrief='Kerberos on 88 plus LDAP naming a domain is a **domain '
            'controller**, and the domain name is the single most valuable '
            'string on the screen: nearly every Active Directory tool takes '
            'it as an argument. Take the name from the scan; do not guess it.',
)

SCENARIOS = [
    Scenario(id='sift-nmap-pinned', track='sift', tier='graded', order=10,
             title='Full-port scan, one service that does not belong',
             body=_PINNED, waypoint='webatk-versionapp', hone=('nmap',),
             source=f'{BOXES}/HackTheBox/Busqueda/Busqueda - Writeup.md'),
    Scenario(id='sift-nmap-oddport', track='sift', tier='graded', order=20,
             title='A sweep with no version detection',
             body=_ODDPORT, waypoint='recon-service-detect', hone=('nmap',),
             source=f'{BOXES}/Proving Grounds/Nibbles/Nibbles - Writeup.md'),
    Scenario(id='sift-nmap-cert', track='sift', tier='graded', order=30,
             title='HTTPS, and a certificate that says too much',
             body=_CERT, waypoint='recon-cert-names', hone=('nmap',),
             source=f'{PLAYBOOK}/02 - Phase 2 - Network & Service Enumeration.md'),
    Scenario(id='sift-nmap-quiet', track='sift', tier='graded', order=40,
             title='Two open ports, both current',
             body=_QUIET, waypoint='web-discovery', hone=('nmap',),
             source=f'{PLAYBOOK}/02 - Phase 2 - Network & Service Enumeration.md'),
    Scenario(id='sift-nmap-dc', track='sift', tier='graded', order=50,
             title='A Windows host with a lot of open ports',
             body=_DC, waypoint='ad-nocred-enum', hone=('nmap',),
             source='Boxes/Active Directory'),
]
