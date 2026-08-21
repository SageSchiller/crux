"""sift: reading Windows local privilege escalation output.

Four scenarios, and the reason this family exists is arithmetic: roughly forty
of the seventy exam points are Windows and Active Directory, and every other
family in this track reads Linux. The reading problems here are Windows-shaped
and do not transfer from `sudo -l`.

The through-line is that **Windows tells you what you can do, in a wall of
rows that all begin `Se`**, and the difference between a service account you
can turn into SYSTEM in one command and one you cannot is a single line in
that wall.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import Note, Priv, TextBlock, WhoamiPriv

WIN = 'Boxes/Windows'
PLAYBOOK = 'PEN-200 Playbook'

# --------------------------------------------------------------------------
# 1. The privilege that ends the box
# --------------------------------------------------------------------------

_IMPERSONATE = MarkBody(
    prompt='You have a shell as a service account on a Windows host. Mark '
           'every line that changes what you do next.',
    fixture=WhoamiPriv(
        user='iis apppool\\vantage',
        privs=(
            Priv('SeImpersonatePrivilege',
                 'Impersonate a client after authentication', 'Enabled',
                 kind='lead',
                 why='The shortest path to SYSTEM on Windows. Held by nearly '
                     'every service account, and the potato family turns it '
                     'into SYSTEM in one command.'),
            Priv('SeCreateGlobalPrivilege', 'Create global objects',
                 'Enabled', kind='decoy',
                 why='It looks the part and grants nothing: creating global '
                     'section objects is a normal service-account permission. '
                     'It keeps company with the real finding, which is why it '
                     'tempts.'),
            Priv('SeAssignPrimaryTokenPrivilege',
                 'Replace a process level token', 'Disabled', kind='decoy',
                 why='Right family, wrong row: it is Disabled, and the enabled '
                     'one above already gives the same outcome. Read the State '
                     'column, not only the name.'),
        ),
    ),
    actions=(
        Action('Run a potato: `PrintSpoofer` first, and keep a second one '
               'staged in case it does not fire.', True,
               '`SeImpersonatePrivilege` on a service account is the shortest '
               'path to SYSTEM on Windows. It is one command, it is reliable, '
               'and it is why this line is the first thing to look for on '
               'every Windows foothold.'),
        Action('Hunt the filesystem for credentials and config files.',
               why='Always worth doing and always slower. You have a token '
                   'privilege that hands you SYSTEM directly; spend it before '
                   'you start reading other people files.'),
        Action('`SeCreateGlobalPrivilege` is enabled: use it to create a '
               'global object and escalate.',
               why='The decoy, and it looks the part. Creating global section '
                   'objects is a normal service-account permission and grants '
                   'no path to SYSTEM on its own. It is enabled on the same '
                   'accounts that have `SeImpersonate`, which is why it keeps '
                   'company with the real finding.'),
        Action('Note `SeAssignPrimaryTokenPrivilege` and look for a token-'
               'stealing exploit.',
               why='Right family, wrong row: it is **Disabled**, and the '
                   'enabled one directly above it already gives you the same '
                   'outcome. Read the State column, not only the name.'),
    ),
    debrief='**`SeImpersonatePrivilege` Enabled is the single most valuable '
            'line on a Windows foothold.** It is held by nearly every service '
            'account (IIS, MSSQL, and anything running as `NETWORK SERVICE`), '
            'and the potato family turns it into SYSTEM in one command. Learn '
            'the rest of the token as furniture: `SeChangeNotify`, '
            '`SeIncreaseWorkingSet`, `SeShutdown`, `SeTimeZone` and '
            '`SeUndock` are on everything. And read the **State** column: a '
            'disabled privilege in this list is still worth noting, but an '
            'enabled `SeImpersonate` is worth acting on now.\n\n'
            'On the box this comes from, `PrintSpoofer` finished it. On '
            'another in the same set, `PrintSpoofer` failed and `GodPotato` '
            'worked, so keep a second one staged rather than concluding the '
            'privilege was a dead end.',
)

# --------------------------------------------------------------------------
# 2. The token with nothing on it (crux D9)
# --------------------------------------------------------------------------

_NO_IMPERSONATE = MarkBody(
    prompt='You have a shell as a normal user on a Windows host. Mark every '
           'line that changes what you do next.',
    fixture=WhoamiPriv(
        user='harbord\\daniel',
        privs=(
            Priv('SeIncreaseWorkingSetPrivilege',
                 'Increase a process working set', 'Disabled', kind='decoy',
                 why='On every account on every Windows machine. Learning the '
                     'stock list by sight is what makes an interesting line '
                     'unmissable when one does appear.'),
        ),
    ),
    actions=(
        Action('Nothing here. The potato family is ruled out, so go look at '
               'scheduled tasks, services and file permissions.', True,
               'Correct, and it is a real result rather than a failure. No '
               '`SeImpersonate` and no `SeBackup` means the token routes are '
               'closed, and knowing that in ten seconds is what stops you '
               'trying six potatoes against a host that can never run one.'),
        Action('Try PrintSpoofer anyway: it sometimes works without the '
               'privilege listed.',
               why='It does not. The potato family exists to abuse '
                   '`SeImpersonate` specifically, and without it on the token '
                   'there is nothing for it to abuse.'),
        Action('`SeIncreaseWorkingSetPrivilege` is unusual: research it.',
               why='It is on every account on every Windows machine, which is '
                   'the whole reason it is on this screen. Learning the stock '
                   'list by sight is what makes the interesting line '
                   'unmissable when it does appear.'),
        Action('Re-run `whoami /priv` from an elevated prompt to see the full '
               'token.',
               why='You do not have an elevated prompt: getting one is the '
                   'thing you are trying to do. This output is the token you '
                   'actually hold.'),
    ),
    debrief='**A token with nothing on it is a result, and it arrives in ten '
            'seconds.** It closes the entire potato family and the backup-'
            'privilege route at once, which is worth far more than it sounds: '
            'those are the fast paths, and knowing they are shut sends you '
            'straight to the slower ones that will actually work here. On the '
            'box this comes from, the answer was a scheduled task whose '
            'script every user could write.',
)

# --------------------------------------------------------------------------
# 3. A script SYSTEM runs and you can write
# --------------------------------------------------------------------------

_ICACLS = MarkBody(
    prompt='A scheduled task on the host runs as SYSTEM. You checked the '
           'permissions on the script it calls. Mark every line that changes '
           'what you do next.',
    fixture=TextBlock(
        header=('C:\\>schtasks /query /fo LIST /v | findstr /C:"Task To Run" '
                '/C:"Run As User"',
                'Task To Run:    C:\\Log-Management\\job.bat',
                'Run As User:    SYSTEM',
                '',
                'C:\\>icacls C:\\Log-Management\\job.bat'),
        rows=(
            Note('C:\\Log-Management\\job.bat NT AUTHORITY\\SYSTEM:(I)(F)'),
            Note('                           BUILTIN\\Administrators:(I)(F)'),
            Note('                           BUILTIN\\Users:(F)', 'lead',
                 why='Full control for every authenticated user, you included, '
                     'over a file the schtasks output says SYSTEM runs. Two '
                     'screens, one finding.'),
            Note('                           NT AUTHORITY\\'
                 'Authenticated Users:(I)(M)', 'decoy',
                 why='Modify would often be enough, but it is inherited (I) '
                     'while the line above is a directly-applied (F). Read the '
                     'flags: (I) inherited, (F) full, (M) modify.'),
        ),
        noise_pool=(
            Note('                           CREATOR OWNER:(I)(OI)(CI)(IO)(F)'),
            Note('                           HARBORD\\daniel:(I)(RX)'),
            Note('                           BUILTIN\\Backup Operators:(I)(RX)'),
            Note('                           NT SERVICE\\TrustedInstaller:(I)(F)'),
        ),
        noise=(1, 3),
        footer=('', 'Successfully processed 1 files; Failed processing 0 files'),
    ),
    actions=(
        Action('Append your payload to `job.bat` and wait for the task to '
               'fire.', True,
               'Two facts on one screen make the finding: SYSTEM runs it, and '
               '`BUILTIN\\Users:(F)` means every authenticated user, you '
               'included, has full control of the file. Whatever you put in '
               'it, SYSTEM runs.'),
        Action('`Authenticated Users:(M)` gives modify: use that instead.',
               why='The near miss. `(M)` is modify and would often be enough, '
                   'but it is inherited `(I)` from the parent directory and '
                   '`(F)` on the line above is the stronger, directly-applied '
                   'grant. Read the flags: `(I)` is inherited, `(F)` is full '
                   'control, `(M)` is modify.'),
        Action('Replace the whole file with your own script.',
               why='It works and it is louder than it needs to be. Appending '
                   'keeps the task doing its real job, which keeps the box '
                   'behaving normally and is the habit worth having on an '
                   'engagement.'),
        Action('Take ownership with `takeown` first.',
               why='You already have full control. Taking ownership is an '
                   'extra, noisier step that changes an ACL you did not need '
                   'to change.'),
    ),
    debrief='**A scheduled task is a finding only when it crosses something '
            'you can write.** Read the two screens together: `Run As User: '
            'SYSTEM` tells you what the task is worth, and `icacls` tells you '
            'whether you can reach it. The flag to learn by sight is '
            '`BUILTIN\\Users:(F)` on anything a privileged account executes. '
            'And read the letters: `(F)` full, `(M)` modify, `(RX)` read and '
            'execute, `(I)` inherited from the parent.',
)

# --------------------------------------------------------------------------
# 4. A service path nobody quoted
# --------------------------------------------------------------------------

_SERVICE = MarkBody(
    prompt='Service configuration on a Windows host, with the directory '
           'permissions beside it. Mark every line that changes what you do '
           'next.',
    fixture=TextBlock(
        header=('C:\\>sc qc SecuritySvc',
                '[SC] QueryServiceConfig SUCCESS',
                ''),
        rows=(
            Note('        SERVICE_NAME: SecuritySvc'),
            Note('        TYPE               : 10  WIN32_OWN_PROCESS'),
            Note('        START_TYPE         : 2   AUTO_START'),
            Note('        BINARY_PATH_NAME   : C:\\Program Files\\Vantage '
                 'Security\\agent service\\agent.exe', 'lead',
                 why='Spaces and no quotes, so Windows tries C:\\Program.exe, '
                     'then C:\\Program Files\\Vantage.exe. Paired with a '
                     'writable directory on that path it is code execution as '
                     'whatever the service runs as.'),
            Note('        SERVICE_START_NAME : LocalSystem', 'decoy',
                 why='It says what the finding is worth, not what the finding '
                     'is. Plenty of services run as LocalSystem and are '
                     'perfectly safe.'),
            Note('        DISPLAY_NAME       : Vantage Security Agent'),
        ),
        noise_pool=(
            Note('        ERROR_CONTROL      : 1   NORMAL'),
            Note('        LOAD_ORDER_GROUP   :'),
            Note('        TAG                : 0'),
            Note('        DEPENDENCIES       : RpcSs'),
        ),
        noise=(2, 4),
        footer=('',
                'C:\\>icacls "C:\\Program Files\\Vantage Security"',
                'C:\\Program Files\\Vantage Security '
                'BUILTIN\\Users:(OI)(CI)(M)',
                '                                '
                'NT AUTHORITY\\SYSTEM:(I)(OI)(CI)(F)'),
    ),
    actions=(
        Action('Drop `Vantage.exe` into `C:\\Program Files\\` and restart the '
               'service, since the unquoted path makes Windows try that name '
               'first.', True,
               'The binary path has spaces and no quotes, so Windows tries '
               '`C:\\Program.exe`, then `C:\\Program Files\\Vantage.exe`, and '
               'so on. The `icacls` line shows Users hold modify on '
               '`Vantage Security`, and the service runs as LocalSystem.'),
        Action('The service runs as LocalSystem: look for a DLL to hijack in '
               'its directory.',
               why='Right instinct, more work. DLL hijacking needs you to '
                   'know which DLL is loaded and missing; the unquoted path '
                   'on the line above needs only a filename you can already '
                   'guess from the path itself.'),
        Action('Reconfigure the service binary with `sc config binPath=`.',
               why='That needs `SERVICE_CHANGE_CONFIG` on the service, which '
                   'a normal user does not have. The unquoted path is the way '
                   'in precisely because it needs no privilege on the service '
                   'at all, only a writable directory.'),
        Action('`AUTO_START` means it runs at boot: plan to reboot the host.',
               why='True, and it is how the payload eventually fires, but on '
                   'its own it is not a finding. Plenty of services auto-'
                   'start and are perfectly safe.'),
    ),
    debrief='**An unquoted service path is only a finding when a directory on '
            'it is writable.** Windows splits an unquoted `BINARY_PATH_NAME` '
            'on spaces and tries each prefix with `.exe` appended, so a path '
            'like `C:\\Program Files\\Vantage Security\\agent service\\'
            'agent.exe` is an invitation at `C:\\Program.exe` and at '
            '`C:\\Program Files\\Vantage.exe`. Read the two together: the '
            'unquoted path names the opportunity, `icacls` says whether you '
            'can take it, and `SERVICE_START_NAME` says what it is worth. '
            '`C:\\` and `C:\\Program Files` are not writable by normal users '
            'on a healthy system, which is why the interesting prefix is '
            'usually the vendor directory further along.',
)

SCENARIOS = [
    Scenario(id='sift-win-priv', track='sift', tier='graded', order=810,
             title='A Windows service account token',
             body=_IMPERSONATE, waypoint='win-potato', hone=('powershell',),
             source=f'{WIN}/Proving Grounds/Craft/Craft - Writeup.md'),
    Scenario(id='sift-win-nopriv', track='sift', tier='graded', order=820,
             title='A Windows user token with nothing on it',
             body=_NO_IMPERSONATE, waypoint='win-baseline',
             hone=('powershell',),
             source=f'{WIN}/HackTheBox/Markup/Markup - Writeup.md'),
    Scenario(id='sift-win-icacls', track='sift', tier='graded', order=830,
             title='A SYSTEM task, and who can write its script',
             body=_ICACLS, waypoint='win-schtask', hone=('powershell',),
             source=f'{WIN}/HackTheBox/Markup/Markup - Writeup.md'),
    Scenario(id='sift-win-service', track='sift', tier='graded', order=840,
             title='A service path nobody quoted',
             body=_SERVICE, waypoint='win-baseline', hone=('powershell',),
             source=f'{PLAYBOOK}/07 - Phase 5 - Windows Privilege Escalation.md'),
]
