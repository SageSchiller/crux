"""sift: reading share enumeration.

Three scenarios. The reading problem is that a Windows host answers with the
same four or five administrative shares every time, so the skill is entirely
**recognising the furniture** in order to see the one row that is not.

One of these has no lead at all (crux D9), and it is the honest common case:
most hosts really do only have the default shares.
"""

from __future__ import annotations

from ...model import Action, MarkBody, Scenario
from ...targets._fixture import Share, SmbShares

AD = 'Boxes/Active Directory'
PLAYBOOK = 'PEN-200 Playbook'

_ODD_SHARE = MarkBody(
    prompt='Anonymous share enumeration against a domain member. Mark every '
           'line that changes what you do next.',
    fixture=SmbShares(
        host='', netbios='FS01', domain='cicada.htb',
        shares=(
            Share('HR', 'Disk', '', kind='lead'),
            Share('DEV', 'Disk', 'Development', kind='decoy'),
            Share('NETLOGON', 'Disk', 'Logon server share', kind='decoy'),
            Share('SYSVOL', 'Disk', 'Logon server share'),
        ),
    ),
    actions=(
        Action('Recurse `HR` and read every file in it.', True,
               'A share with a business name that anonymous access reached is '
               'the finding. Departmental shares hold onboarding documents, '
               'and onboarding documents hold starting passwords.'),
        Action('Look in `DEV` first: developers leave credentials.',
               why='A good instinct and often true, but read the listing '
                   'again. It is on the screen and you could not open it; '
                   '`HR` you could. Chase what you can already reach.'),
        Action('Search `SYSVOL` for a Groups.xml with a cpassword in it.',
               why='A real and excellent technique, and worth doing once you '
                   'have a domain credential. `SYSVOL` normally needs an '
                   'authenticated session, and you have not got one yet.'),
        Action('Try `ADMIN$` and `C$` to see whether anonymous has admin.',
               why='They are on every Windows host and they are the first '
                   'thing anonymous is denied. Their presence is not '
                   'information.'),
    ),
    debrief='**Four or five shares are furniture: `ADMIN$`, `C$`, `IPC$`, '
            '`print$`, and on a DC `SYSVOL` and `NETLOGON`.** Learn them by '
            'sight so that anything else on the list stands out immediately. '
            'A share named after a department is somebody storing documents, '
            'and documents written by people contain credentials written by '
            'people.',
)

_SIGNING = MarkBody(
    prompt='Protocol-level enumeration against a host on the internal '
           'network. Mark every line that changes what you do next.',
    fixture=SmbShares(
        host='', netbios='WEB01', domain='corp.local', style='nxc',
        signing=False,
        os_name='Windows Server 2019 Build 17763 x64',
        shares=(
            Share('wwwroot', 'Disk', '', 'READ', kind='decoy'),
        ),
    ),
    actions=(
        Action('Note that SMB signing is not required here, and line this '
               'host up as a relay target.', True,
               '`signing:False` is the precondition for NTLM relay. It turns '
               'any authentication you can coerce out of another account into '
               'a session on this host, and it is a property of the host '
               'rather than of anything you have found on it.'),
        Action('Read the `wwwroot` share for source and connection strings.',
               why='Worth doing and genuinely productive sometimes. But it is '
                   'a file hunt, and the banner just told you about a '
                   'structural weakness in how the host authenticates.'),
        Action('Note the build number and search for a kernel exploit.',
               why='A build number on a screen is not a vulnerability. This '
                   'is the reflex that turns enumeration output into a search '
                   'engine query instead of a plan.'),
        Action('Nothing here: it is one host with one uninteresting share.',
               why='The whole point of the scenario. The share list is dull '
                   'and the **banner** is the finding, which is exactly the '
                   'line people skip because it looks like a header.'),
    ),
    debrief='In this output the banner is not a header, it is a **finding**. '
            'Domain name, OS build, and above all `signing:False` are all in '
            'it. Signing not being required is the single most valuable '
            'property a host can advertise to you on an internal network, and '
            'it is printed above the part everybody reads.',
)

_DEFAULTS_ONLY = MarkBody(
    prompt='Anonymous share enumeration against a file server. Mark every '
           'line that changes what you do next.',
    fixture=SmbShares(
        host='', netbios='SRV02', domain='corp.local',
        shares=(
            Share('IPC$', 'IPC', 'Remote IPC', kind='decoy'),
        ),
    ),
    actions=(
        Action('Nothing here. Anonymous sees only the default shares, so move '
               'on and come back with a credential.', True,
               'Correct, and the discipline this scenario is built to train. '
               'Every host shows this list. Seeing it means the enumeration '
               'worked and found nothing, which is a result, not a failure.'),
        Action('`IPC$` is listed, so try enumerating users through it with '
               'RID cycling.',
               why='Genuinely worth trying, and the closest thing to a real '
                   'answer here, which is why it is the tempting one. But '
                   '`IPC$` is present on every Windows host ever built. Its '
                   'appearance in this list is not the reason to try RID '
                   'cycling, and treating it as one means you will "find" it '
                   'on every host you ever scan.'),
        Action('Brute-force share names with a wordlist to find hidden ones.',
               why='Hidden shares end in `$` and are not hidden from an '
                   'authenticated enumeration. This is hours of traffic for '
                   'something a credential would answer in one command.'),
        Action('Retry with `--option=client min protocol=NT1` in case shares '
               'are hidden behind SMB1.',
               why='The listing already fell back to SMB1 and failed at the '
                   'bottom of the screen. Repeating a step the output shows '
                   'you already took is the shape of not wanting to leave.'),
    ),
    debrief='**The default share list is the null result, and recognising a '
            'null result quickly is a scored skill.** `ADMIN$`, `C$`, `IPC$`, '
            '`print$` and nothing else means anonymous access got you '
            'nowhere. The correct next move is a credential, not another '
            'angle on the same empty listing.',
)

SCENARIOS = [
    Scenario(id='sift-smb-share', track='sift', tier='graded', order=310,
             title='Share listing on a domain member',
             body=_ODD_SHARE, waypoint='svc-smb', hone=('impacket',),
             source=f'{AD}/HackTheBox/Cicada/Cicada - Writeup.md'),
    Scenario(id='sift-smb-signing', track='sift', tier='graded', order=320,
             title='One share, and a banner nobody reads',
             body=_SIGNING, waypoint='ad-nocred-enum', hone=('impacket',),
             source=f'{PLAYBOOK}/08 - Phase 6 - Active Directory.md'),
    Scenario(id='sift-smb-defaults', track='sift', tier='graded', order=330,
             title='Share listing on a file server',
             body=_DEFAULTS_ONLY, waypoint='svc-smb', hone=('impacket',),
             source=f'{PLAYBOOK}/02 - Phase 2 - Network & Service Enumeration.md'),
]
