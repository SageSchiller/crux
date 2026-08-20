"""sift: reading `sudo -l`.

Three scenarios, and a different reading problem from the other two families.
A scan is furniture with an anomaly in it; a discovery run is repetition with
an outlier in it. `sudo -l` is short, every line is deliberate, and the
question is not "which line stands out" but **"which of these grants has a way
out of the program it names"**.

That is why two of these have several plausible-looking grants and one real
one: the failure being trained is not missing the line, it is not knowing
which named binary hands you a shell.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import Grant, SudoL

BOXES = 'Boxes/Linux'

# --------------------------------------------------------------------------
# 1. A wildcard in the argument list
# --------------------------------------------------------------------------

_WILDCARD = MarkBody(
    prompt='You have a shell as `www-data`. Mark every line that changes what '
           'you do next.',
    fixture=SudoL(
        user='www-data', host='lavita',
        grants=(
            Grant('(root) NOPASSWD: /usr/bin/composer --working-dir=/var/www/'
                  'html/lavita *', kind='lead'),
            Grant('(root) NOPASSWD: /usr/bin/systemctl daemon-reload',
                  kind='decoy'),
            Grant('(root) NOPASSWD: /usr/sbin/logrotate -f /etc/logrotate.conf'),
            Grant('(root) NOPASSWD: /usr/bin/id'),
        ),
    ),
    actions=(
        Action('Abuse the trailing `*`: put a `composer.json` with a script '
               'in the working directory and let composer run it as root.',
               True,
               'The wildcard is the finding. It lets you pass arguments the '
               'sudoers author never enumerated, and composer runs scripts '
               'from a file you control in a directory you can write to.'),
        Action('Use `systemctl daemon-reload` to reload a unit file you wrote.',
               why='The near miss, and a good instinct. `daemon-reload` alone '
                   'only re-reads unit files; without a matching grant to '
                   '`start` or `enable` something, nothing you wrote ever '
                   'runs. Check what the grant does not include.'),
        Action('Exploit `logrotate -f` against a config you control.',
               why='The path is fixed to `/etc/logrotate.conf`, which you '
                   'cannot write. No wildcard, no argument injection, no way '
                   'in.'),
        Action('Run `sudo id` to confirm the sudo rules work at all.',
               why='Free, harmless, and tells you nothing you do not already '
                   'have on the screen.'),
    ),
    debrief='**A wildcard in a sudoers rule is almost always the answer.** It '
            'means the author enumerated a command but not its arguments, and '
            'arguments are where programs are told to do things their author '
            'did not have in mind. Read every grant for the difference '
            'between a fixed command line and one with a `*`, a directory you '
            'can write to, or a filename you control.',
)

# --------------------------------------------------------------------------
# 2. A binary that hands you a shell
# --------------------------------------------------------------------------

_GTFO = MarkBody(
    prompt='You have a shell as `puma`. Mark every line that changes what you '
           'do next.',
    fixture=SudoL(
        user='puma', host='sau',
        grants=(
            Grant('(ALL : ALL) NOPASSWD: /usr/bin/systemctl status '
                  'trail.service', kind='lead'),
            Grant('(ALL : ALL) NOPASSWD: /usr/bin/journalctl --no-pager -u '
                  'trail.service', kind='decoy'),
            Grant('(ALL : ALL) NOPASSWD: /usr/bin/uptime'),
        ),
    ),
    actions=(
        Action('Run the `systemctl status` grant, let it page, and escape to '
               'a shell from the pager.', True,
               'It is a fixed command with no wildcard, which is why it looks '
               'safe. The way out is not in the arguments, it is that '
               '`systemctl status` pipes through a pager, and a pager takes '
               '`!sh`.'),
        Action('Use the `journalctl` grant to reach a pager instead.',
               why='The same class of trick and a genuinely good instinct, '
                   'but read the grant: `--no-pager` is already on the '
                   'command line, and it is fixed. The author closed this one '
                   'and left the other open.'),
        Action('Nothing here: all three are fixed commands with no wildcards.',
               why='The reasoning that makes this scenario worth doing. No '
                   'wildcard is necessary when the program itself will hand '
                   'you a shell. A fixed command line is not a safe one.'),
        Action('Try `sudo uptime` and read the load averages for a clue.',
               why='Reads the machine, changes nothing.'),
    ),
    debrief='Wildcards are the obvious way a sudo grant goes wrong and not '
            'the only one. **Ask what the named program can be persuaded to '
            'do, not just what arguments you can add**: anything that pages, '
            'edits, compiles, archives, or runs a script is a shell waiting '
            'to happen. That question has a reference answer, and it is '
            'GTFOBins.',
)

# --------------------------------------------------------------------------
# 3. A wall of grants
# --------------------------------------------------------------------------

_WALL = MarkBody(
    prompt='You have a shell on a monitoring host. The account has a lot of '
           'sudo rules. Mark every line that changes what you do next.',
    fixture=SudoL(
        user='nagios', host='monitored',
        grants=(
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios start'),
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios stop'),
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios restart'),
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios reload'),
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios status'),
            Grant('(ALL) NOPASSWD: /etc/init.d/nagios checkconfig'),
            Grant('(ALL) NOPASSWD: /usr/bin/systemctl start nagios.service'),
            Grant('(ALL) NOPASSWD: /usr/bin/systemctl stop nagios.service'),
            Grant('(ALL) NOPASSWD: /usr/bin/systemctl restart nagios.service'),
            Grant('(ALL) NOPASSWD: /usr/bin/systemctl reload nagios.service'),
            Grant('(ALL) NOPASSWD: /usr/bin/systemctl status nagios.service',
                  kind='decoy'),
            Grant('(ALL) NOPASSWD: /usr/local/nagios/bin/nagios -v '
                  '/usr/local/nagios/etc/nagios.cfg'),
            Grant('(ALL) NOPASSWD: /usr/local/nagiosxi/scripts/'
                  'manage_services.sh *', kind='lead'),
            Grant('(ALL) NOPASSWD: /usr/local/nagiosxi/scripts/'
                  'reset_config_perms.sh'),
            Grant('(ALL) NOPASSWD: /usr/local/nagiosxi/scripts/'
                  'backup_xi.sh'),
        ),
    ),
    actions=(
        Action('Read `manage_services.sh` and drive it with the argument the '
               'wildcard lets you pass.', True,
               'Fourteen of these are fixed command lines against a named '
               'service. One takes arbitrary arguments and is a shell script '
               'you can read first. That asymmetry is the whole screen.'),
        Action('Work through the init scripts: one of `start`/`stop`/'
               '`restart` may run something writable.',
               why='Worth a thought and it is where the volume of the screen '
                   'pushes you. But they are fixed command lines against a '
                   'root-owned init script, and there are ten of them '
                   'precisely because they are boring.'),
        Action('Use `systemctl status nagios.service` and escape from the '
               'pager.',
               why='The right trick, spotted on the wrong screen, which makes '
                   'it the most instructive wrong answer here. It is a real '
                   'technique and worth trying, but a wildcard on a readable '
                   'script is a shorter and more reliable path than a pager '
                   'escape that a `--no-pager` default may have closed.'),
        Action('Run `backup_xi.sh` and look for credentials in the archive.',
               why='Plausible, and it may even work eventually. But it is a '
                   'fixed command producing an artifact you then have to '
                   'search, which is two uncertain steps where the wildcard '
                   'is one.'),
    ),
    debrief='**Volume is a hiding place.** Twenty near-identical grants are '
            'not twenty findings, they are one pattern plus whatever does not '
            'fit it. Read for the shape first: fixed command lines against a '
            'named service are furniture, and the row that takes an argument '
            'is the one to read.',
)

SCENARIOS = [
    Scenario(id='sift-sudo-wildcard', track='sift', tier='graded', order=210,
             title='Four sudo grants, one with a star in it',
             body=_WILDCARD, waypoint='lin-sudo', hone=('linuxadv',),
             source=f'{BOXES}/Proving Grounds/LaVita/LaVita - Writeup.md'),
    Scenario(id='sift-sudo-gtfo', track='sift', tier='graded', order=220,
             title='Three sudo grants, none with a wildcard',
             body=_GTFO, waypoint='lin-sudo-script', hone=('linuxadv',),
             source=f'{BOXES}/HackTheBox/Sau/Sau - Writeup.md'),
    Scenario(id='sift-sudo-wall', track='sift', tier='graded', order=230,
             title='Fifteen sudo grants',
             body=_WALL, waypoint='lin-sudo-probe', hone=('linuxadv',),
             source=f'{BOXES}/HackTheBox/Monitored/Monitored - Writeup.md'),
]
