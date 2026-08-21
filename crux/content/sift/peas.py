"""sift: reading local enumeration output.

Four scenarios, and the purest form of the skill in the whole track. A local
enumeration script prints thousands of lines of which almost all are the
distribution as shipped, and the entire job is knowing what stock looks like
so that a deviation from it is visible.

The failure being trained is specific and it is not laziness: it is that
**everything in this output looks slightly interesting**, so an untrained
reader marks fifteen things, chases all of them, and finds the real one an
hour later or not at all.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import Note, PeasChunk, Section

BOXES = 'Boxes/Linux'
PLAYBOOK = 'PEN-200 Playbook'

#: Every one of these ships SUID on a stock Debian or Ubuntu. Reading them as
#: findings is the single most common way an hour disappears.
_STOCK_SUID = (
    Note('-rwsr-xr-x 1 root root   72K Nov 24  2024 /usr/bin/su'),
    Note('-rwsr-xr-x 1 root root   55K Nov 24  2024 /usr/bin/mount'),
    Note('-rwsr-xr-x 1 root root   39K Nov 24  2024 /usr/bin/umount'),
    Note('-rwsr-xr-x 1 root root   62K Nov 24  2024 /usr/bin/chfn'),
    Note('-rwsr-xr-x 1 root root   52K Nov 24  2024 /usr/bin/chsh'),
    Note('-rwsr-xr-x 1 root root   88K Nov 24  2024 /usr/bin/gpasswd'),
    Note('-rwsr-xr-x 1 root root   68K Nov 24  2024 /usr/bin/passwd',
         'decoy',
         why='SUID root on every Linux system in the world, because it has to '
             'be. So are su, mount, umount, chfn, chsh and newgrp: learn the '
             'list by sight and the screen empties out.'),
    Note('-rwsr-xr-x 1 root root   44K Nov 24  2024 /usr/bin/newgrp'),
    Note('-rwsr-xr-- 1 root messagebus 51K Oct  1  2024 '
         '/usr/lib/dbus-1.0/dbus-daemon-launch-helper'),
    Note('-rwsr-xr-x 1 root root  463K Jan 15  2025 /usr/lib/openssh/ssh-keysign'),
)

_NET_ROWS = (
    Note('tcp   LISTEN 0  128   0.0.0.0:22      0.0.0.0:*'),
    Note('tcp   LISTEN 0  511   0.0.0.0:80      0.0.0.0:*'),
)

_KERNEL = Section('Basic information', (
    Note('OS: Linux version 5.15.0-119-generic'),
    Note('User & Groups: uid=33(www-data) gid=33(www-data) groups=33(www-data)'),
    Note('Hostname: app01'),
    Note('Writable folder: /dev/shm'),
))

# --------------------------------------------------------------------------
# 1. A SUID binary that is not stock
# --------------------------------------------------------------------------

_SUID = MarkBody(
    prompt='Local enumeration as `www-data`. Mark every line that changes '
           'what you do next.',
    fixture=PeasChunk(sections=(
        _KERNEL,
        Section('SUID - Check easy privesc, exploits and write perms',
                _STOCK_SUID[:6] + (
                    Note('-rwsr-xr-x 1 root root   17K Mar  3  2026 '
                         '/usr/local/bin/sysinfo', 'lead',
                         why='Not part of any distribution, SUID root, and '
                             'dated this year while everything around it is '
                             'the install date. A locally written SUID helper '
                             'is the most productive thing on a Linux box.'),
                ) + _STOCK_SUID[6:9]),
        Section('Capabilities', (
            Note('/usr/bin/ping = cap_net_raw+ep', 'decoy',
                 why='Stock, and `cap_net_raw` grants raw sockets, not file '
                     'reads or code as root. A capability matters only when it '
                     'is on something unusual and is one of the dangerous '
                     'ones.'),
            Note('/usr/bin/mtr-packet = cap_net_raw+ep'),
        )),
        Section('Active Ports', _NET_ROWS),
    )),
    actions=(
        Action('Run `sysinfo`, then `strings` it to see what it shells out to.',
               True,
               'It is not part of any distribution, it is SUID root, and its '
               'timestamp is this year while everything around it is the '
               'install date. A locally written SUID helper is the most '
               'productive thing on a Linux box.'),
        Action('Look up a `pkexec` or `polkit` local privilege escalation.',
               why='It is not even in this listing. Reaching for a named CVE '
                   'before reading what is actually on the screen is the '
                   'reflex this whole track exists to break.'),
        Action('Exploit `/usr/bin/passwd` being SUID root.',
               why='`passwd` is SUID root on every Linux system in the world, '
                   'because it has to be. So are `su`, `mount`, `umount`, '
                   '`chfn`, `chsh`, `gpasswd` and `newgrp`. Learn this list '
                   'by sight and the screen empties out.'),
        Action('Abuse `cap_net_raw` on `ping` to escalate.',
               why='Also stock, and `cap_net_raw` lets you craft packets, not '
                   'read files or run code as root. A capability is only '
                   'interesting when it is on something unusual, and when it '
                   'is one of the dangerous ones.'),
    ),
    debrief='**Learn the stock SUID list by sight.** `su`, `mount`, `umount`, '
            '`chfn`, `chsh`, `gpasswd`, `passwd`, `newgrp`, '
            '`dbus-daemon-launch-helper`, `ssh-keysign`, and on many systems '
            '`pkexec` and `sudo`. Once those are furniture, a locally '
            'compiled binary in `/usr/local/bin` with this year on it is '
            'impossible to miss, and it is where the path usually runs.',
)

# --------------------------------------------------------------------------
# 2. A cron job with a writable target
# --------------------------------------------------------------------------

_CRON = MarkBody(
    prompt='Local enumeration as `karen`. Mark every line that changes what '
           'you do next.',
    fixture=PeasChunk(sections=(
        _KERNEL,
        Section('Cron jobs', (
            Note('/etc/cron.d/e2scrub_all: 30 3 * * 0 root /usr/lib/x86_64-'
                 'linux-gnu/e2fsprogs/e2scrub_all_cron'),
            Note('/etc/crontab: 17 *  * * *  root  cd / && run-parts --report '
                 '/etc/cron.hourly'),
            Note('/etc/crontab: */5 * * * * root /opt/scripts/backup.sh',
                 'lead',
                 why='Root runs this every five minutes. On its own that is '
                     'not a finding; paired with the writable path further '
                     'down the screen it is the whole box.'),
            Note('/etc/cron.daily/apt-compat: root'),
            Note('/etc/cron.daily/dpkg: root'),
            Note('/etc/cron.weekly/man-db: root'),
        )),
        Section('Interesting writable files owned by me or writable by everyone',
                (
                    Note('/tmp'),
                    Note('/var/tmp'),
                    Note('/dev/shm'),
                    Note('/opt/scripts/backup.sh', 'lead',
                         why='You can write it, and the cron section says root '
                             'runs it. Neither line is interesting alone, '
                             'which is exactly why this is worth practising.'),
                    Note('/var/www/html/uploads', 'decoy',
                         why='World-writable, and you are already on the box. '
                             'A web shell there runs as the same account you '
                             'already have.'),
                )),
        Section('SUID - Check easy privesc, exploits and write perms',
                _STOCK_SUID[:5]),
    )),
    actions=(
        Action('Append a reverse shell to `/opt/scripts/backup.sh` and wait '
               'up to five minutes.', True,
               'Two lines on two different parts of the screen make one '
               'finding: root runs it, and you can write it. Neither line is '
               'interesting on its own, which is exactly why this is worth '
               'practising.'),
        Action('Write a web shell into `/var/www/html/uploads`, since it is '
               'world-writable.',
               why='You are already on the box. A web shell there runs as the '
                   'same `www-data` you could already reach, so it moves you '
                   'sideways at best.'),
        Action('Investigate `e2scrub_all_cron`, which runs weekly as root.',
               why='Real, root, and shipped by `e2fsprogs`. Root-owned, '
                   'root-writable, and identical on every Debian system. '
                   'A cron job is only a finding when something in its path '
                   'is yours.'),
        Action('Look for a `run-parts` hijack via `/etc/cron.hourly`.',
               why='A good idea against a directory you can write to, and '
                   '`/etc/cron.hourly` is not in the writable list. Check the '
                   'writable list before designing the attack.'),
    ),
    debrief='**A cron job is a finding only when it crosses a writable path.** '
            'Read the two sections together: the schedule tells you what runs '
            'as root, the writable list tells you what you control, and the '
            'answer is always in the intersection. Neither list alone is '
            'worth marking.',
)

# --------------------------------------------------------------------------
# 3. Credentials in a config file
# --------------------------------------------------------------------------

_CREDS = MarkBody(
    prompt='Local enumeration as `www-data` on an application server. Mark '
           'every line that changes what you do next.',
    fixture=PeasChunk(sections=(
        _KERNEL,
        Section('Analyzing .conf files', (
            Note('/etc/apache2/sites-enabled/000-default.conf: DocumentRoot '
                 '/var/www/html'),
            Note('/var/www/html/config.php: define("DB_USER", "webapp");'),
            Note('/var/www/html/config.php: define("DB_PASS", '
                 '"Summer2025!Rotate");', 'lead',
                 why='A password a person chose. It is not a password for the '
                     'database so much as a password for this person: spray it '
                     'at every local account with a shell before spending it '
                     'where it was found.'),
            Note('/etc/php/8.2/apache2/php.ini: expose_php = On', 'decoy',
                 why='A real misconfiguration and a useless one: it discloses '
                     'a version number to somebody already inside the '
                     'machine.'),
        )),
        Section('Users with console', (
            Note('root:x:0:0:root:/root:/bin/bash'),
            Note('karen:x:1000:1000::/home/karen:/bin/bash'),
            Note('backupsvc:x:1001:1001::/home/backupsvc:/bin/bash'),
        )),
        Section('Active Ports', _NET_ROWS + (
            Note('tcp   LISTEN 0  70    127.0.0.1:3306  0.0.0.0:*', 'decoy',
                 why='What the credential is actually for, which is why it is '
                     'tempting. Reading application data is a lateral step; '
                     'the local accounts with shells are the vertical one.'),
        )),
    )),
    actions=(
        Action('Try the database password against every local account with a '
               'shell, starting with `karen` and `backupsvc`.', True,
               'People reuse passwords across accounts far more reliably than '
               'they patch. A found credential is worth spraying at the '
               'shells on the same box before it is worth using where it was '
               'found.'),
        Action('Log into MySQL on 127.0.0.1:3306 with it and read the '
               'application tables.',
               why='It will work, and it is what the credential is actually '
                   'for, which is why this is the tempting answer. But '
                   'reading application data is a lateral step; the two local '
                   'accounts with shells are the vertical one.'),
        Action('`expose_php = On` leaks the PHP version in headers: use it to '
               'find a matching exploit.',
               why='A real misconfiguration and a genuinely useless one. It '
                   'discloses a version number to someone who is already '
                   'inside the machine.'),
        Action('Crack the root password hash out of `/etc/shadow`.',
               why='`www-data` cannot read `/etc/shadow`. The listing here is '
                   '`/etc/passwd`, which has had no hashes in it since the '
                   'nineties.'),
    ),
    debrief='**A password found in a config file is not a password for that '
            'service, it is a password for this person.** Spray it at every '
            'local account with a shell before you spend it on the database '
            'it was written for. Reuse is the single highest-yield habit in '
            'local privilege escalation.',
)

# --------------------------------------------------------------------------
# 4. A clean box (crux D9)
# --------------------------------------------------------------------------

_CLEAN = MarkBody(
    prompt='Local enumeration as `www-data` on a hardened host. Mark every '
           'line that changes what you do next.',
    fixture=PeasChunk(sections=(
        _KERNEL,
        Section('SUID - Check easy privesc, exploits and write perms',
                _STOCK_SUID),
        Section('Cron jobs', (
            Note('/etc/crontab: 17 *  * * *  root  cd / && run-parts --report '
                 '/etc/cron.hourly'),
            Note('/etc/cron.daily/apt-compat: root'),
            Note('/etc/cron.daily/dpkg: root'),
            Note('/etc/cron.weekly/man-db: root'),
        )),
        Section('Interesting writable files owned by me or writable by everyone',
                (
                    Note('/tmp'),
                    Note('/var/tmp'),
                    Note('/dev/shm'),
                )),
        Section('Capabilities', (
            Note('/usr/bin/ping = cap_net_raw+ep', 'decoy',
                 why='Stock, and it grants raw sockets. There is no path from '
                     'crafting packets to reading root-owned files.'),
        )),
    )),
    actions=(
        Action('Nothing here. Go back to the application and look for a '
               'credential or a second service.', True,
               'Every SUID is stock, every cron is shipped, and the only '
               'writable directories are the three that are world-writable on '
               'every Linux system alive. This output is a clean bill of '
               'health, and recognising one quickly is worth more than '
               'another pass over it.'),
        Action('Search for a kernel exploit against 5.15.0-119.',
               why='Where this screen sends people, and almost always wrong '
                   'on an exam. Kernel exploits are unreliable, they crash '
                   'hosts you need, and the version being visible is not '
                   'evidence that one exists.'),
        Action('Abuse `cap_net_raw` on `ping`.',
               why='Stock, and it grants raw sockets. There is no path from '
                   'crafting packets to reading root-owned files.'),
        Action('Write to `/dev/shm` and look for a race condition.',
               why='World-writable on every Linux host. Its appearance in '
                   'this list is the list working correctly, not a finding.'),
    ),
    debrief='**A clean enumeration is a result.** The value of knowing the '
            'stock lists by sight is not that it finds things faster, it is '
            'that it lets you say "there is nothing here" with enough '
            'confidence to leave. On a box with no local privilege escalation '
            'in it, the fastest route to root runs back through the '
            'application.',
)

SCENARIOS = [
    Scenario(id='sift-peas-suid', track='sift', tier='graded', order=410,
             title='Local enumeration: the SUID list',
             body=_SUID, waypoint='lin-suid-triage', hone=('linuxadv',),
             source=f'{PLAYBOOK}/06 - Phase 5 - Linux Privilege Escalation.md'),
    Scenario(id='sift-peas-cron', track='sift', tier='graded', order=420,
             title='Local enumeration: schedules and writable paths',
             body=_CRON, waypoint='lin-cron', hone=('linuxadv',),
             source=f'{PLAYBOOK}/06 - Phase 5 - Linux Privilege Escalation.md'),
    Scenario(id='sift-peas-creds', track='sift', tier='graded', order=430,
             title='Local enumeration: a config file with a password in it',
             body=_CREDS, waypoint='lin-creds', hone=('linuxadv',),
             source='Boxes/00 - Privesc Quick Reference.md'),
    Scenario(id='sift-peas-clean', track='sift', tier='graded', order=440,
             title='Local enumeration on a hardened host',
             body=_CLEAN, waypoint='lin-enum', hone=('linuxadv',),
             source=f'{PLAYBOOK}/06 - Phase 5 - Linux Privilege Escalation.md'),
]
